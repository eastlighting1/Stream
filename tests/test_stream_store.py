from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from spine.models import CorrelationRefs, MetricPayload, MetricRecord, RecordEnvelope

from stream import IntegrityState, ReplayError, ReplayMode, ScanFilter, StoreConfig, StreamStore


def _cli_env() -> dict[str, str]:
    env = os.environ.copy()
    current = env.get("PYTHONPATH", "")
    extra = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = extra if not current else os.pathsep.join([extra, current])
    return env


def _metric_record(sequence: int = 1) -> dict[str, object]:
    stamp = f"2026-04-03T00:00:0{sequence}Z"
    return {
        "record_ref": f"record/train-step-{sequence}",
        "record_type": "metric",
        "recorded_at": stamp,
        "observed_at": stamp,
        "producer_ref": "scribe.python.local",
        "run_ref": "run/train-1",
        "stage_execution_ref": "stage/train",
        "operation_context_ref": f"op/train-step-{sequence}",
        "correlation_refs": {"trace_id": "trace/train-1"},
        "completeness_marker": "complete",
        "degradation_marker": "none",
        "schema_version": "1.0.0",
        "payload": {
            "metric_key": "training.loss",
            "value": 0.4 + sequence,
            "value_type": "scalar",
            "aggregation_scope": "step",
            "tags": {"device": "cuda:0"},
        },
    }


def _copy_fixture(name: str, destination: Path) -> Path:
    source = Path(__file__).parent / "fixtures" / name
    shutil.copytree(source, destination)
    return destination


def test_append_and_scan_records(tmp_path: Path) -> None:
    store = StreamStore.open(StoreConfig(root_path=tmp_path / "store"))

    result = store.append(_metric_record())

    assert result.success is True
    assert result.accepted_count == 1
    assert result.durable_count == 1
    assert result.accepted[0].durability_status.value in {"flushed", "fsynced"}

    scanned = list(store.scan(ScanFilter(run_ref="run/train-1")))
    assert len(scanned) == 1
    assert scanned[0].record["record_type"] == "metric"
    assert scanned[0].record["payload"]["metric_key"] == "training.loss"


def test_append_many_reports_partial_failures(tmp_path: Path) -> None:
    store = StreamStore.open(StoreConfig(root_path=tmp_path / "store"))

    result = store.append_many(
        [
            _metric_record(1),
            {"record_type": "metric", "payload": {}},
            _metric_record(2),
        ]
    )

    assert result.accepted_count == 2
    assert result.rejected_count == 1
    assert "record[1] rejected" in result.rejected[0]


def test_replay_spine_record_objects(tmp_path: Path) -> None:
    store = StreamStore.open(StoreConfig(root_path=tmp_path / "store"))
    record = MetricRecord(
        envelope=RecordEnvelope(
            record_ref="record/train-step-1",
            record_type="metric",
            recorded_at="2026-04-03T00:00:01Z",
            observed_at="2026-04-03T00:00:01Z",
            producer_ref="scribe.python.local",
            run_ref="run/train-1",
            stage_execution_ref="stage/train",
            operation_context_ref="op/train-step-1",
            correlation_refs=CorrelationRefs(trace_id="trace/train-1"),
        ),
        payload=MetricPayload(
            metric_key="training.loss",
            value=0.42,
            value_type="scalar",
            aggregation_scope="step",
            tags={"device": "cuda:0"},
        ),
    )

    store.append(record)
    replay = store.replay(ScanFilter(record_type="metric"))

    assert replay.record_count == 1
    assert replay.records[0].record["payload"]["metric_key"] == "training.loss"


def test_segment_rollover_creates_multiple_segments(tmp_path: Path) -> None:
    store = StreamStore.open(StoreConfig(root_path=tmp_path / "store", max_segment_bytes=250))

    store.append_many([_metric_record(1), _metric_record(2), _metric_record(3)])

    segments = sorted((tmp_path / "store" / "segments").glob("segment-*.jsonl"))
    assert len(segments) >= 2


def test_integrity_detects_corrupted_json_lines(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    store = StreamStore.open(StoreConfig(root_path=store_root))
    store.append(_metric_record())

    segment_path = store_root / "segments" / "segment-000001.jsonl"
    with segment_path.open("a", encoding="utf-8") as handle:
        handle.write("{not-json}\n")

    report = store.check_integrity()

    assert report.healthy is False
    assert any(issue.code == "invalid_json_line" for issue in report.issues)


def test_segment_file_contains_json_entries(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    store = StreamStore.open(StoreConfig(root_path=store_root))
    store.append(_metric_record())

    segment_path = store_root / "segments" / "segment-000001.jsonl"
    lines = segment_path.read_text(encoding="utf-8").strip().splitlines()
    payload = json.loads(lines[0])

    assert payload["sequence"] == 1
    assert payload["record"]["run_ref"] == "run/train-1"


def test_manifest_tracks_last_committed_sequence(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    store = StreamStore.open(StoreConfig(root_path=store_root))
    store.append_many([_metric_record(1), _metric_record(2)])

    manifest = json.loads((store_root / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["next_sequence"] == 3
    assert manifest["last_committed_sequence"] == 2
    assert manifest["current_segment_record_count"] == 2
    assert manifest["layout_mode"] == "jsonl_segments"


def test_append_writes_derivative_indexes(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    store = StreamStore.open(StoreConfig(root_path=store_root))

    store.append(_metric_record())

    run_index = store_root / "indexes" / "run_ref" / "run__train-1.jsonl"
    record_type_index = store_root / "indexes" / "record_type" / "metric.jsonl"

    assert run_index.exists()
    assert record_type_index.exists()

    run_index_payload = json.loads(run_index.read_text(encoding="utf-8").splitlines()[0])
    assert run_index_payload["sequence"] == 1


def test_scan_works_with_indexed_filter(tmp_path: Path) -> None:
    store = StreamStore.open(StoreConfig(root_path=tmp_path / "store"))
    store.append_many([_metric_record(1), _metric_record(2)])

    records = list(store.scan(ScanFilter(record_type="metric")))

    assert len(records) == 2
    assert [record.sequence for record in records] == [1, 2]


def test_cli_scan_outputs_records(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    store = StreamStore.open(StoreConfig(root_path=store_root))
    store.append(_metric_record())

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "stream.cli",
            "--store",
            str(store_root),
            "scan",
            "--run-ref",
            "run/train-1",
        ],
        check=True,
        capture_output=True,
        env=_cli_env(),
        text=True,
    )

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1
    assert json.loads(lines[0])["run_ref"] == "run/train-1"


def test_cli_integrity_outputs_report(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    store = StreamStore.open(StoreConfig(root_path=store_root))
    store.append(_metric_record())

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "stream.cli",
            "--store",
            str(store_root),
            "integrity",
        ],
        check=True,
        capture_output=True,
        env=_cli_env(),
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["healthy"] is True
    assert payload["record_count"] == 1
    assert payload["state"] == "healthy"


def test_strict_replay_fails_on_corrupted_store(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    store = StreamStore.open(StoreConfig(root_path=store_root))
    store.append(_metric_record())

    segment_path = store_root / "segments" / "segment-000001.jsonl"
    with segment_path.open("a", encoding="utf-8") as handle:
        handle.write("{not-json}")

    try:
        store.replay(mode=ReplayMode.STRICT)
    except ReplayError:
        pass
    else:
        raise AssertionError("strict replay should fail on corrupted history")


def test_tolerant_replay_surfaces_known_gaps(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    store = StreamStore.open(StoreConfig(root_path=store_root))
    store.append(_metric_record())

    segment_path = store_root / "segments" / "segment-000001.jsonl"
    with segment_path.open("a", encoding="utf-8") as handle:
        handle.write("{not-json}")

    replay = store.replay(mode=ReplayMode.TOLERANT)

    assert replay.record_count == 1
    assert replay.known_gaps
    assert replay.warnings


def test_export_jsonl_writes_replayed_history(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    store = StreamStore.open(StoreConfig(root_path=store_root))
    store.append_many([_metric_record(1), _metric_record(2)])

    export_path = tmp_path / "exports" / "train.jsonl"
    result = store.export_jsonl(export_path, ScanFilter(run_ref="run/train-1"))

    assert result.record_count == 2
    assert export_path.exists()
    lines = export_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_cli_replay_outputs_tolerant_metadata(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    store = StreamStore.open(StoreConfig(root_path=store_root))
    store.append(_metric_record())

    segment_path = store_root / "segments" / "segment-000001.jsonl"
    with segment_path.open("a", encoding="utf-8") as handle:
        handle.write("{not-json}")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "stream.cli",
            "--store",
            str(store_root),
            "replay",
            "--mode",
            "tolerant",
        ],
        check=True,
        capture_output=True,
        env=_cli_env(),
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["mode"] == "tolerant"
    assert payload["record_count"] == 1
    assert payload["known_gaps"]


def test_cli_export_writes_file(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    store = StreamStore.open(StoreConfig(root_path=store_root))
    store.append_many([_metric_record(1), _metric_record(2)])
    export_path = tmp_path / "cli-export" / "train.jsonl"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "stream.cli",
            "--store",
            str(store_root),
            "export",
            "--output",
            str(export_path),
            "--run-ref",
            "run/train-1",
        ],
        check=True,
        capture_output=True,
        env=_cli_env(),
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["record_count"] == 2
    assert export_path.exists()


def test_rebuild_indexes_restores_missing_helper_files(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    store = StreamStore.open(StoreConfig(root_path=store_root))
    store.append_many([_metric_record(1), _metric_record(2)])

    shutil.rmtree(store_root / "indexes")
    report = store.rebuild_indexes()

    assert report.success is True
    assert report.rebuilt_indexes is True
    assert report.integrity_state == IntegrityState.HEALTHY
    assert (store_root / "indexes" / "run_ref" / "run__train-1.jsonl").exists()


def test_rebuild_indexes_warns_when_store_is_corrupted(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    store = StreamStore.open(StoreConfig(root_path=store_root))
    store.append(_metric_record())

    segment_path = store_root / "segments" / "segment-000001.jsonl"
    with segment_path.open("a", encoding="utf-8") as handle:
        handle.write("{not-json}")

    report = store.rebuild_indexes()

    assert report.success is False
    assert report.rebuilt_indexes is True
    assert report.integrity_state == IntegrityState.CORRUPTED
    assert report.warnings


def test_repair_truncated_tail_restores_strict_replay(tmp_path: Path) -> None:
    store_root = _copy_fixture("store_v1_truncated", tmp_path / "store")
    store = StreamStore.open(StoreConfig(root_path=store_root))

    pre_report = store.check_integrity()
    assert pre_report.state == "corrupted"

    repair = store.repair_truncated_tails()

    assert repair.success is True
    assert repair.repaired_segments == (1,)
    assert repair.quarantined_paths
    assert repair.integrity_state == IntegrityState.HEALTHY

    replay = store.replay(mode=ReplayMode.STRICT)
    assert replay.record_count == 1


def test_fixture_store_v1_clean_replays_successfully(tmp_path: Path) -> None:
    store_root = _copy_fixture("store_v1_clean", tmp_path / "store")
    store = StreamStore.open(StoreConfig(root_path=store_root))

    report = store.check_integrity()
    replay = store.replay()

    assert report.healthy is True
    assert replay.record_count == 1


def test_cli_repair_command_repairs_truncated_tail(tmp_path: Path) -> None:
    store_root = _copy_fixture("store_v1_truncated", tmp_path / "store")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "stream.cli",
            "--store",
            str(store_root),
            "repair",
        ],
        check=True,
        capture_output=True,
        env=_cli_env(),
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["repaired_segments"] == [1]


def test_cli_rebuild_indexes_command_restores_indexes(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    store = StreamStore.open(StoreConfig(root_path=store_root))
    store.append(_metric_record())
    shutil.rmtree(store_root / "indexes")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "stream.cli",
            "--store",
            str(store_root),
            "rebuild-indexes",
        ],
        check=True,
        capture_output=True,
        env=_cli_env(),
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["rebuilt_indexes"] is True
    assert payload["integrity_state"] == "healthy"


def test_replay_checks_integrity_once_per_replay_call(tmp_path: Path) -> None:
    from stream.replay.service import ReplayService

    store = StreamStore.open(StoreConfig(root_path=tmp_path / "store"))
    store.append(_metric_record())

    class CountingIntegrity:
        def __init__(self) -> None:
            self.calls = 0

        def check(self) -> object:
            self.calls += 1
            return store.check_integrity()

    counting = CountingIntegrity()
    replay = ReplayService(store._reader, counting)  # type: ignore[arg-type]

    result = replay.replay()

    assert result.record_count == 1
    assert counting.calls == 1
