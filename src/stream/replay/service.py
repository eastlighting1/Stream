"""Replay services for canonical stored history."""

from __future__ import annotations

from collections.abc import Iterator

from ..exceptions import ReplayError
from ..integrity import IntegrityChecker
from ..models import (
    IntegrityReport,
    IntegrityState,
    ReplayMode,
    ReplayResult,
    ScanFilter,
    StoredRecord,
)
from ..reader import RecordReader


class ReplayService:
    """Replay stored records without adding projection semantics."""

    def __init__(self, reader: RecordReader, integrity: IntegrityChecker) -> None:
        self._reader = reader
        self._integrity = integrity

    def iter_replay(
        self,
        scan_filter: ScanFilter | None = None,
        *,
        mode: ReplayMode = ReplayMode.STRICT,
    ) -> Iterator[StoredRecord]:
        integrity = self._check_integrity(mode)
        return self._iter_replay(scan_filter, mode=mode, integrity=integrity)

    def replay(
        self,
        scan_filter: ScanFilter | None = None,
        *,
        mode: ReplayMode = ReplayMode.STRICT,
    ) -> ReplayResult:
        integrity = self._check_integrity(mode)
        records = tuple(self._iter_replay(scan_filter, mode=mode, integrity=integrity))
        warnings = tuple(issue.message for issue in integrity.issues)
        known_gaps = tuple(
            f"{issue.code}@segment={issue.segment_id}:line={issue.line_number}"
            for issue in integrity.issues
            if issue.severity == "error"
        )
        return ReplayResult(
            records=records,
            record_count=len(records),
            mode=mode,
            warnings=warnings if mode == ReplayMode.TOLERANT else (),
            known_gaps=known_gaps if mode == ReplayMode.TOLERANT else (),
        )

    def _check_integrity(self, mode: ReplayMode) -> IntegrityReport:
        integrity = self._integrity.check()
        if mode == ReplayMode.STRICT and integrity.state == IntegrityState.CORRUPTED:
            raise ReplayError("strict replay is not allowed while the store is corrupted")
        return integrity

    def _iter_replay(
        self,
        scan_filter: ScanFilter | None,
        *,
        mode: ReplayMode,
        integrity: IntegrityReport,
    ) -> Iterator[StoredRecord]:
        del integrity
        return self._reader.scan(
            scan_filter,
            tolerate_corruption=mode == ReplayMode.TOLERANT,
        )
