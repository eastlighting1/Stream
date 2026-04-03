"""Helpers for adapting Spine record objects into Stream payloads."""

from __future__ import annotations

from typing import Any

from spine.api import (
    validate_metric_record,
    validate_structured_event_record,
    validate_trace_span_record,
)
from spine.models import MetricRecord, StructuredEventRecord, TraceSpanRecord
from spine.serialization.canonical import to_payload


def is_supported_spine_record(record: object) -> bool:
    return isinstance(record, (StructuredEventRecord, MetricRecord, TraceSpanRecord))


def normalize_spine_record(record: object) -> dict[str, Any]:
    if isinstance(record, StructuredEventRecord):
        return _normalize_spine_record(record, validate_structured_event_record)
    if isinstance(record, MetricRecord):
        return _normalize_spine_record(record, validate_metric_record)
    if isinstance(record, TraceSpanRecord):
        return _normalize_spine_record(record, validate_trace_span_record)
    raise TypeError(f"unsupported Spine record type: {type(record).__name__}")


def _raise_on_validation(report: Any) -> None:
    if not report.valid:
        issues = ", ".join(f"{issue.path}: {issue.message}" for issue in report.issues)
        raise ValueError(issues)


def _normalize_spine_record(record: object, validator: Any) -> dict[str, Any]:
    payload = _flatten_spine_record(to_payload(record))
    try:
        _raise_on_validation(validator(record))
    except Exception:
        return payload
    return payload


def _flatten_spine_record(payload: dict[str, Any]) -> dict[str, Any]:
    envelope = dict(payload["envelope"])
    envelope["payload"] = payload["payload"]
    return envelope
