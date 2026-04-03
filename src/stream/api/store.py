"""Public store API."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from ..config import StoreConfig
from ..export import ExportService
from ..integrity import IntegrityChecker
from ..layout import LayoutManager
from ..models import (
    AppendResult,
    IntegrityReport,
    RepairReport,
    ReplayMode,
    ReplayResult,
    ScanFilter,
    StoredRecord,
)
from ..reader import RecordReader
from ..repair import RepairService
from ..replay import ReplayService
from ..writer import RecordWriter


class StreamStore:
    """Append-oriented store for canonical record history."""

    def __init__(self, config: StoreConfig) -> None:
        self._layout = LayoutManager(config)
        self._writer = RecordWriter(self._layout)
        self._reader = RecordReader(self._layout)
        self._integrity = IntegrityChecker(self._layout)
        self._replay = ReplayService(self._reader, self._integrity)
        self._export = ExportService(self._replay)
        self._repair = RepairService(self._layout, self._integrity, self._reader)

    @classmethod
    def open(cls, config: StoreConfig) -> StreamStore:
        return cls(config)

    @property
    def config(self) -> StoreConfig:
        return self._layout.config

    def append(self, record: object) -> AppendResult:
        return self._writer.append(record)

    def append_many(self, records: list[object] | tuple[object, ...]) -> AppendResult:
        return self._writer.append_many(records)

    def scan(self, scan_filter: ScanFilter | None = None) -> Iterator[StoredRecord]:
        return self._reader.scan(scan_filter)

    def replay(
        self,
        scan_filter: ScanFilter | None = None,
        *,
        mode: ReplayMode = ReplayMode.STRICT,
    ) -> ReplayResult:
        return self._replay.replay(scan_filter, mode=mode)

    def iter_replay(
        self,
        scan_filter: ScanFilter | None = None,
        *,
        mode: ReplayMode = ReplayMode.STRICT,
    ) -> Iterator[StoredRecord]:
        return self._replay.iter_replay(scan_filter, mode=mode)

    def check_integrity(self) -> IntegrityReport:
        return self._integrity.check()

    def export_jsonl(
        self,
        destination: str | Path,
        scan_filter: ScanFilter | None = None,
        *,
        mode: ReplayMode = ReplayMode.STRICT,
    ) -> ReplayResult:
        return self._export.export_jsonl(Path(destination), scan_filter, mode=mode)

    def rebuild_indexes(self) -> RepairReport:
        return self._repair.rebuild_indexes()

    def repair_truncated_tails(self) -> RepairReport:
        return self._repair.repair_truncated_tails()
