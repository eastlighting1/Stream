"""Repair and rebuild services for local Stream stores."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ..integrity import IntegrityChecker
from ..layout import LayoutManager
from ..models import IntegrityState, RepairReport
from ..reader import RecordReader


class RepairService:
    """Perform safe local repair steps for known damaged-store cases."""

    def __init__(
        self,
        layout: LayoutManager,
        integrity: IntegrityChecker,
        reader: RecordReader,
    ) -> None:
        self._layout = layout
        self._integrity = integrity
        self._reader = reader

    def rebuild_indexes(self) -> RepairReport:
        integrity = self._integrity.check()
        records = [
            {
                "sequence": stored.sequence,
                "segment_id": stored.segment_id,
                "offset": stored.offset,
                "run_ref": stored.record["run_ref"],
                "stage_execution_ref": stored.record.get("stage_execution_ref"),
                "record_type": stored.record["record_type"],
            }
            for stored in self._reader.scan(tolerate_corruption=True)
        ]
        self._layout.index.rebuild(records)
        warnings: list[str] = []
        success = integrity.state == IntegrityState.HEALTHY
        notes = ["Derivative indexes were rebuilt from canonical segments."]
        if integrity.state != IntegrityState.HEALTHY:
            warnings.append(
                "Indexes were rebuilt from a store with integrity issues; "
                "damaged records were skipped."
            )
            notes.append("Re-run integrity checks after repairing canonical segments.")
        return RepairReport(
            success=success,
            rebuilt_indexes=True,
            integrity_state=integrity.state,
            notes=tuple(notes),
            warnings=tuple(warnings),
        )

    def repair_truncated_tails(self) -> RepairReport:
        repaired_segments: list[int] = []
        quarantined_paths: list[str] = []
        notes: list[str] = []
        for segment_id in self._layout.iter_segment_ids():
            path = self._layout.segment_path(segment_id)
            with path.open("r", encoding="utf-8") as handle:
                lines = handle.readlines()
            if not lines:
                continue
            try:
                json.loads(lines[-1])
                continue
            except json.JSONDecodeError:
                quarantine_path = self._quarantine_copy(path)
                quarantined_paths.append(str(quarantine_path))
                valid_prefix: list[str] = []
                for line in lines:
                    try:
                        json.loads(line)
                    except json.JSONDecodeError:
                        break
                    valid_prefix.append(line if line.endswith("\n") else f"{line}\n")
                path.write_text("".join(valid_prefix), encoding="utf-8")
                repaired_segments.append(segment_id)
                notes.append(f"trimmed damaged tail from segment {segment_id}")
        if repaired_segments:
            self._recompute_manifest()
            rebuild = self.rebuild_indexes()
            report = self._integrity.check()
            return RepairReport(
                success=report.healthy,
                repaired_segments=tuple(repaired_segments),
                quarantined_paths=tuple(quarantined_paths),
                rebuilt_indexes=rebuild.rebuilt_indexes,
                integrity_state=report.state,
                notes=tuple(notes + list(rebuild.notes)),
                warnings=tuple(list(rebuild.warnings) + list(report.recommendations)),
            )
        report = self._integrity.check()
        return RepairReport(
            success=report.healthy,
            integrity_state=report.state,
            notes=("no truncated tail repairs were required",),
            warnings=tuple(report.recommendations),
        )

    def _recompute_manifest(self) -> None:
        highest_sequence = 0
        current_segment_id = 1
        for segment_id in self._layout.iter_segment_ids():
            current_segment_id = max(current_segment_id, segment_id)
            path = self._layout.segment_path(segment_id)
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    highest_sequence = max(highest_sequence, int(entry["sequence"]))
        manifest = self._layout.load_manifest()
        manifest["current_segment_id"] = current_segment_id
        manifest["last_committed_sequence"] = highest_sequence
        manifest["next_sequence"] = highest_sequence + 1
        current_segment_path = self._layout.segment_path(current_segment_id)
        if current_segment_path.exists():
            with current_segment_path.open("r", encoding="utf-8") as handle:
                manifest["current_segment_record_count"] = sum(1 for line in handle if line.strip())
        else:
            manifest["current_segment_record_count"] = 0
        self._layout.save_manifest(manifest)

    def _quarantine_copy(self, source: Path) -> Path:
        quarantine_dir = self._layout.root_path / "quarantine"
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        destination = quarantine_dir / source.name
        suffix = 1
        while destination.exists():
            destination = quarantine_dir / f"{source.stem}.{suffix}{source.suffix}"
            suffix += 1
        shutil.copy2(source, destination)
        return destination
