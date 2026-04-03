"""Append and batch-append services."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import UTC, datetime

from ..config import DurabilityMode
from ..exceptions import AppendError, RecordValidationError
from ..layout import LayoutManager
from ..models import AppendReceipt, AppendResult, DurabilityStatus
from ..models.records import normalize_record


class RecordWriter:
    """Append canonical records into Stream segments."""

    def __init__(self, layout: LayoutManager) -> None:
        self._layout = layout

    def append(self, record: object) -> AppendResult:
        return self.append_many([record])

    def append_many(self, records: Iterable[object]) -> AppendResult:
        accepted: list[AppendReceipt] = []
        rejected: list[str] = []
        for index, record in enumerate(records):
            try:
                accepted.append(self._append_one(record))
            except RecordValidationError as exc:
                rejected.append(f"record[{index}] rejected: {exc}")
            except Exception as exc:  # pragma: no cover
                raise AppendError("append failed unexpectedly") from exc
        durability_status = _batch_durability_status(accepted)
        return AppendResult(
            accepted=tuple(accepted),
            rejected=tuple(rejected),
            durability_status=durability_status,
            durable_count=len(accepted),
        )

    def _append_one(self, record: object) -> AppendReceipt:
        canonical = normalize_record(record)
        slot = self._layout.begin_append()
        entry = {
            "sequence": slot.sequence,
            "appended_at": _utc_now(),
            "record": canonical,
        }
        path = self._layout.segment_path(slot.segment_id)
        encoded = json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n"
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded)
            handle.flush()
            if self._layout.config.durability_mode == DurabilityMode.FSYNC:
                os.fsync(handle.fileno())
                durability_status = DurabilityStatus.FSYNCED
            else:
                durability_status = DurabilityStatus.FLUSHED
        self._layout.commit_append(slot)
        self._layout.index.append(
            sequence=slot.sequence,
            segment_id=slot.segment_id,
            offset=slot.offset,
            run_ref=str(canonical["run_ref"]),
            stage_execution_ref=_optional_string(canonical.get("stage_execution_ref")),
            record_type=str(canonical["record_type"]),
        )
        return AppendReceipt(
            sequence=slot.sequence,
            segment_id=slot.segment_id,
            offset=slot.offset,
            record_ref=str(canonical["record_ref"]),
            record_type=str(canonical["record_type"]),
            run_ref=str(canonical["run_ref"]),
            durability_status=durability_status,
        )


def _utc_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _batch_durability_status(
    receipts: list[AppendReceipt],
) -> DurabilityStatus:
    if not receipts:
        return DurabilityStatus.ACCEPTED
    if all(
        receipt.durability_status == DurabilityStatus.FSYNCED
        for receipt in receipts
    ):
        return DurabilityStatus.FSYNCED
    if all(
        receipt.durability_status in {DurabilityStatus.FSYNCED, DurabilityStatus.FLUSHED}
        for receipt in receipts
    ):
        return DurabilityStatus.FLUSHED
    return DurabilityStatus.ACCEPTED
