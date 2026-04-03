"""Layout state models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AppendSlot:
    """A deterministic append slot selected before data is committed."""

    segment_id: int
    sequence: int
    offset: int
