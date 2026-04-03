"""Sequential record reader and scan filters."""

from __future__ import annotations

import json
from collections.abc import Iterator

from ..layout import LayoutManager
from ..models import ScanFilter, StoredRecord


class RecordReader:
    """Read records from Stream segments in append order."""

    def __init__(self, layout: LayoutManager) -> None:
        self._layout = layout

    def scan(
        self,
        scan_filter: ScanFilter | None = None,
        *,
        tolerate_corruption: bool = False,
    ) -> Iterator[StoredRecord]:
        scan_filter = scan_filter or ScanFilter()
        if _can_use_index(scan_filter):
            yield from self._scan_indexed(
                scan_filter,
                tolerate_corruption=tolerate_corruption,
            )
            return
        for segment_id in self._layout.iter_segment_ids():
            path = self._layout.segment_path(segment_id)
            with path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        if tolerate_corruption:
                            continue
                        raise
                    stored = StoredRecord(
                        sequence=int(entry["sequence"]),
                        segment_id=segment_id,
                        offset=line_number,
                        appended_at=str(entry["appended_at"]),
                        record=dict(entry["record"]),
                    )
                    if _matches(stored, scan_filter):
                        yield stored

    def _scan_indexed(
        self,
        scan_filter: ScanFilter,
        *,
        tolerate_corruption: bool,
    ) -> Iterator[StoredRecord]:
        family, value = _index_lookup(scan_filter)
        if family is None or value is None:
            return
        entries = self._layout.index.lookup(family, value)
        grouped: dict[int, set[int]] = {}
        for entry in entries:
            grouped.setdefault(entry.segment_id, set()).add(entry.offset)
        for segment_id in sorted(grouped):
            line_numbers = grouped[segment_id]
            path = self._layout.segment_path(segment_id)
            with path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if line_number not in line_numbers or not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        if tolerate_corruption:
                            continue
                        raise
                    stored = StoredRecord(
                        sequence=int(entry["sequence"]),
                        segment_id=segment_id,
                        offset=line_number,
                        appended_at=str(entry["appended_at"]),
                        record=dict(entry["record"]),
                    )
                    if _matches(stored, scan_filter):
                        yield stored


def _matches(stored: StoredRecord, scan_filter: ScanFilter) -> bool:
    record = stored.record
    if scan_filter.run_ref is not None and record.get("run_ref") != scan_filter.run_ref:
        return False
    if (
        scan_filter.stage_execution_ref is not None
        and record.get("stage_execution_ref") != scan_filter.stage_execution_ref
    ):
        return False
    if scan_filter.record_type is not None and record.get("record_type") != scan_filter.record_type:
        return False
    recorded_at = record.get("recorded_at")
    if (
        scan_filter.start_time is not None
        and isinstance(recorded_at, str)
        and recorded_at < scan_filter.start_time
    ):
        return False
    if (
        scan_filter.end_time is not None
        and isinstance(recorded_at, str)
        and recorded_at > scan_filter.end_time
    ):
        return False
    return True


def _can_use_index(scan_filter: ScanFilter) -> bool:
    if scan_filter.start_time is not None or scan_filter.end_time is not None:
        return False
    populated = sum(
        value is not None
        for value in (
            scan_filter.run_ref,
            scan_filter.stage_execution_ref,
            scan_filter.record_type,
        )
    )
    return populated == 1


def _index_lookup(scan_filter: ScanFilter) -> tuple[str | None, str | None]:
    if scan_filter.run_ref is not None:
        return "run_ref", scan_filter.run_ref
    if scan_filter.stage_execution_ref is not None:
        return "stage_execution_ref", scan_filter.stage_execution_ref
    if scan_filter.record_type is not None:
        return "record_type", scan_filter.record_type
    return None, None
