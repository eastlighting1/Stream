"""Local segment layout management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import StoreConfig
from ..exceptions import LayoutError
from ..indexing import LightweightIndex
from .models import AppendSlot


class LayoutManager:
    """Manage local segment layout and manifest state."""

    def __init__(self, config: StoreConfig) -> None:
        self.config = config
        self._root = config.root_path
        self._segments = self._root / "segments"
        self._manifest_path = self._root / "manifest.json"
        self._ensure_layout()
        self._index = LightweightIndex(self._root, enabled=config.enable_indexes)

    @property
    def root_path(self) -> Path:
        return self._root

    @property
    def segments_path(self) -> Path:
        return self._segments

    @property
    def index(self) -> LightweightIndex:
        return self._index

    def segment_path(self, segment_id: int) -> Path:
        return self._segments / f"segment-{segment_id:06d}.jsonl"

    def load_manifest(self) -> dict[str, Any]:
        try:
            return dict(json.loads(self._manifest_path.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            raise LayoutError("manifest.json is not valid JSON") from exc

    def save_manifest(self, manifest: dict[str, Any]) -> None:
        self._manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def begin_append(self) -> AppendSlot:
        manifest = self.load_manifest()
        segment_id = int(manifest["current_segment_id"])
        segment_path = self.segment_path(segment_id)
        current_segment_record_count = self._current_segment_record_count(manifest)
        if segment_path.exists() and segment_path.stat().st_size >= self.config.max_segment_bytes:
            segment_id += 1
            current_segment_record_count = 0
        sequence = int(manifest["next_sequence"])
        self.segment_path(segment_id).touch(exist_ok=True)
        return AppendSlot(
            segment_id=segment_id,
            sequence=sequence,
            offset=current_segment_record_count + 1,
        )

    def commit_append(self, slot: AppendSlot) -> None:
        manifest = self.load_manifest()
        manifest["current_segment_id"] = slot.segment_id
        manifest["next_sequence"] = slot.sequence + 1
        manifest["last_committed_sequence"] = slot.sequence
        manifest["current_segment_record_count"] = slot.offset
        self.save_manifest(manifest)

    def iter_segment_ids(self) -> list[int]:
        ids: list[int] = []
        for path in sorted(self._segments.glob("segment-*.jsonl")):
            suffix = path.stem.replace("segment-", "")
            ids.append(int(suffix))
        return ids

    def _ensure_layout(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        self._segments.mkdir(parents=True, exist_ok=True)
        if not self._manifest_path.exists():
            self.save_manifest(
                {
                    "layout_mode": self.config.layout_mode,
                    "layout_version": self.config.layout_version,
                    "current_segment_id": 1,
                    "next_sequence": 1,
                    "last_committed_sequence": 0,
                    "current_segment_record_count": 0,
                }
            )

    def _current_segment_record_count(self, manifest: dict[str, Any]) -> int:
        current = manifest.get("current_segment_record_count")
        if current is not None:
            return int(current)
        segment_id = int(manifest["current_segment_id"])
        path = self.segment_path(segment_id)
        if not path.exists():
            return 0
        with path.open("r", encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())
