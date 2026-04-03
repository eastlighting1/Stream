"""Configuration models for Stream."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class DurabilityMode(StrEnum):
    FLUSH = "flush"
    FSYNC = "fsync"


class LayoutMode(StrEnum):
    JSONL_SEGMENTS = "jsonl_segments"


@dataclass(frozen=True, slots=True)
class StoreConfig:
    root_path: Path
    max_segment_bytes: int = 1_048_576
    durability_mode: DurabilityMode = DurabilityMode.FSYNC
    layout_mode: LayoutMode = LayoutMode.JSONL_SEGMENTS
    layout_version: str = "1"
    enable_indexes: bool = True

    def __post_init__(self) -> None:
        if self.max_segment_bytes <= 0:
            raise ValueError("max_segment_bytes must be > 0")
