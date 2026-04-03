"""Lightweight CLI for Stream operations."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .api import StreamStore
from .config import StoreConfig
from .models import ReplayMode, ScanFilter


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    store = StreamStore.open(StoreConfig(root_path=Path(args.store)))

    if args.command == "scan":
        scan_filter = _build_scan_filter(args)
        for record in store.scan(scan_filter):
            print(json.dumps(record.record, sort_keys=True))
        return 0

    if args.command == "replay":
        replay = store.replay(_build_scan_filter(args), mode=ReplayMode(args.mode))
        payload = {
            "mode": replay.mode,
            "record_count": replay.record_count,
            "warnings": list(replay.warnings),
            "known_gaps": list(replay.known_gaps),
            "records": [record.record for record in replay.records],
        }
        print(json.dumps(payload, sort_keys=True))
        return 0

    if args.command == "export":
        replay = store.export_jsonl(
            args.output,
            _build_scan_filter(args),
            mode=ReplayMode(args.mode),
        )
        print(
            json.dumps(
                {
                    "output": str(Path(args.output)),
                    "mode": replay.mode,
                    "record_count": replay.record_count,
                },
                sort_keys=True,
            )
        )
        return 0

    if args.command == "integrity":
        report = store.check_integrity()
        print(
            json.dumps(
                {
                    "healthy": report.healthy,
                    "state": report.state,
                    "segment_count": report.segment_count,
                    "record_count": report.record_count,
                    "issues": [asdict(issue) for issue in report.issues],
                    "recommendations": list(report.recommendations),
                },
                sort_keys=True,
            )
        )
        return 0

    if args.command == "rebuild-indexes":
        repair_report = store.rebuild_indexes()
        print(json.dumps(_repair_payload(repair_report), sort_keys=True))
        return 0

    if args.command == "repair":
        repair_report = store.repair_truncated_tails()
        print(json.dumps(_repair_payload(repair_report), sort_keys=True))
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stream-cli")
    parser.add_argument("--store", required=True, help="Path to the local Stream store")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan stored records")
    scan_parser.add_argument("--run-ref")
    scan_parser.add_argument("--stage-ref")
    scan_parser.add_argument("--record-type")
    scan_parser.add_argument("--start-time")
    scan_parser.add_argument("--end-time")

    replay_parser = subparsers.add_parser("replay", help="Replay stored history")
    replay_parser.add_argument("--run-ref")
    replay_parser.add_argument("--stage-ref")
    replay_parser.add_argument("--record-type")
    replay_parser.add_argument("--start-time")
    replay_parser.add_argument("--end-time")
    replay_parser.add_argument(
        "--mode",
        choices=[mode.value for mode in ReplayMode],
        default=ReplayMode.STRICT.value,
    )

    export_parser = subparsers.add_parser("export", help="Export replayed history to JSONL")
    export_parser.add_argument("--run-ref")
    export_parser.add_argument("--stage-ref")
    export_parser.add_argument("--record-type")
    export_parser.add_argument("--start-time")
    export_parser.add_argument("--end-time")
    export_parser.add_argument(
        "--mode",
        choices=[mode.value for mode in ReplayMode],
        default=ReplayMode.STRICT.value,
    )
    export_parser.add_argument("--output", required=True)

    subparsers.add_parser("integrity", help="Run an integrity check")
    subparsers.add_parser(
        "rebuild-indexes",
        help="Rebuild derivative indexes from canonical segments",
    )
    subparsers.add_parser(
        "repair",
        help="Repair truncated segment tails and rebuild derivative indexes",
    )
    return parser


def _build_scan_filter(args: argparse.Namespace) -> ScanFilter:
    return ScanFilter(
        run_ref=getattr(args, "run_ref", None),
        stage_execution_ref=getattr(args, "stage_ref", None),
        record_type=getattr(args, "record_type", None),
        start_time=getattr(args, "start_time", None),
        end_time=getattr(args, "end_time", None),
    )


def _repair_payload(report: object) -> dict[str, object]:
    return {
        "success": getattr(report, "success", False),
        "repaired_segments": list(getattr(report, "repaired_segments", ())),
        "quarantined_paths": list(getattr(report, "quarantined_paths", ())),
        "rebuilt_indexes": getattr(report, "rebuilt_indexes", False),
        "integrity_state": getattr(report, "integrity_state", None),
        "notes": list(getattr(report, "notes", ())),
        "warnings": list(getattr(report, "warnings", ())),
    }


if __name__ == "__main__":
    raise SystemExit(main())
