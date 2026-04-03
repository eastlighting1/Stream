"""Derivative lightweight indexes for practical local scans."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class IndexEntry:
    """Pointer into canonical stored history."""

    sequence: int
    segment_id: int
    offset: int


class LightweightIndex:
    """Maintain derivative JSONL indexes keyed by common scan filters."""

    def __init__(self, root_path: Path, *, enabled: bool) -> None:
        self._root = root_path / "indexes"
        self._enabled = enabled
        if enabled:
            self._root.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        *,
        sequence: int,
        segment_id: int,
        offset: int,
        run_ref: str,
        stage_execution_ref: str | None,
        record_type: str,
    ) -> None:
        if not self._enabled:
            return
        entry = {"sequence": sequence, "segment_id": segment_id, "offset": offset}
        self._append_to_key("run_ref", run_ref, entry)
        self._append_to_key("record_type", record_type, entry)
        if stage_execution_ref is not None:
            self._append_to_key("stage_execution_ref", stage_execution_ref, entry)

    def lookup(self, family: str, value: str) -> tuple[IndexEntry, ...]:
        if not self._enabled:
            return ()
        path = self._key_path(family, value)
        if not path.exists():
            return ()
        entries: list[IndexEntry] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                payload = json.loads(line)
                entries.append(
                    IndexEntry(
                        sequence=int(payload["sequence"]),
                        segment_id=int(payload["segment_id"]),
                        offset=int(payload["offset"]),
                    )
                )
        return tuple(entries)

    def clear(self) -> None:
        """Remove all derivative index files."""
        if not self._enabled or not self._root.exists():
            return
        for path in sorted(self._root.rglob("*.jsonl"), reverse=True):
            path.unlink()
        for directory in sorted(
            (path for path in self._root.rglob("*") if path.is_dir()),
            reverse=True,
        ):
            try:
                directory.rmdir()
            except OSError:
                continue

    def rebuild(self, records: list[dict[str, object]]) -> None:
        """Rebuild derivative indexes from canonical stored records."""
        if not self._enabled:
            return
        self.clear()
        self._root.mkdir(parents=True, exist_ok=True)
        for record in records:
            self.append(
                sequence=_as_int(record["sequence"]),
                segment_id=_as_int(record["segment_id"]),
                offset=_as_int(record["offset"]),
                run_ref=str(record["run_ref"]),
                stage_execution_ref=_optional_string(record.get("stage_execution_ref")),
                record_type=str(record["record_type"]),
            )

    def _append_to_key(self, family: str, value: str, entry: dict[str, int]) -> None:
        family_path = self._root / family
        family_path.mkdir(parents=True, exist_ok=True)
        path = self._key_path(family, value)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n")

    def _key_path(self, family: str, value: str) -> Path:
        safe = value.replace("/", "__").replace("\\", "__").replace(":", "_")
        return self._root / family / f"{safe}.jsonl"


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _as_int(value: Any) -> int:
    return int(value)
