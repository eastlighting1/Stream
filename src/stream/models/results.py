"""Operational models for append, scan, replay, and integrity."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class DurabilityStatus(StrEnum):
    """Visibility of append durability for a stored record."""

    ACCEPTED = "accepted"
    FLUSHED = "flushed"
    FSYNCED = "fsynced"


class ReplayMode(StrEnum):
    """Replay semantics used when reading potentially damaged history."""

    STRICT = "strict"
    TOLERANT = "tolerant"


class IntegrityState(StrEnum):
    """High-level health classification for the local store."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CORRUPTED = "corrupted"


@dataclass(frozen=True, slots=True)
class AppendReceipt:
    sequence: int
    segment_id: int
    offset: int
    record_ref: str
    record_type: str
    run_ref: str
    durability_status: DurabilityStatus = DurabilityStatus.ACCEPTED


@dataclass(frozen=True, slots=True)
class AppendResult:
    accepted: tuple[AppendReceipt, ...] = ()
    rejected: tuple[str, ...] = ()
    durability_status: DurabilityStatus = DurabilityStatus.ACCEPTED
    durable_count: int = 0

    @property
    def accepted_count(self) -> int:
        return len(self.accepted)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)

    @property
    def success(self) -> bool:
        return self.rejected_count == 0


@dataclass(frozen=True, slots=True)
class ScanFilter:
    run_ref: str | None = None
    stage_execution_ref: str | None = None
    record_type: str | None = None
    start_time: str | None = None
    end_time: str | None = None


@dataclass(frozen=True, slots=True)
class StoredRecord:
    sequence: int
    segment_id: int
    offset: int
    appended_at: str
    record: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ReplayResult:
    records: tuple[StoredRecord, ...]
    record_count: int
    mode: ReplayMode = ReplayMode.STRICT
    warnings: tuple[str, ...] = ()
    known_gaps: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class IntegrityIssue:
    severity: str
    code: str
    message: str
    segment_id: int | None = None
    line_number: int | None = None


@dataclass(frozen=True, slots=True)
class IntegrityReport:
    healthy: bool
    issues: tuple[IntegrityIssue, ...] = ()
    segment_count: int = 0
    record_count: int = 0
    state: IntegrityState = IntegrityState.HEALTHY
    recommendations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RepairReport:
    success: bool
    repaired_segments: tuple[int, ...] = ()
    quarantined_paths: tuple[str, ...] = ()
    rebuilt_indexes: bool = False
    integrity_state: IntegrityState = IntegrityState.HEALTHY
    notes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
