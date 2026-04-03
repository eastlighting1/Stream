"""Canonical mapping normalization and field-level validation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from ..contracts import (
    validate_optional_stable_ref,
    validate_stable_ref,
    validate_string_mapping,
    validate_supported_schema_version,
    validate_timestamp_field,
)
from ..exceptions import RecordValidationError
from .payload_validation import require_allowed, require_non_blank, validate_record_payload

_RECORD_TYPES = frozenset(
    {"structured_event", "metric", "trace_span", "degradation_marker"}
)
_COMPLETENESS_MARKERS = frozenset({"complete", "partial", "unknown"})
_DEGRADATION_MARKERS = frozenset(
    {"none", "partial_failure", "capture_gap", "compatibility_upgrade"}
)


def normalize_mapping_record(record: Mapping[str, Any]) -> dict[str, Any]:
    normalized = {str(key): value for key, value in record.items()}
    payload = normalized.get("payload")
    if not isinstance(payload, Mapping):
        raise RecordValidationError("payload must be a mapping")
    normalized["payload"] = dict(
        validate_string_mapping(payload, "payload", allow_any_values=True)
    )
    correlation_refs = normalized.get("correlation_refs", {})
    if correlation_refs is None:
        correlation_refs = {}
    if not isinstance(correlation_refs, Mapping):
        raise RecordValidationError("correlation_refs must be a mapping when present")
    normalized["correlation_refs"] = {str(key): correlation_refs[key] for key in correlation_refs}
    return normalized


def validate_mapping_record(record: Mapping[str, Any]) -> None:
    validate_stable_ref(record.get("record_ref"), "record_ref")
    require_non_blank(record.get("record_type"), "record_type")
    validate_timestamp_field(record.get("recorded_at"), "recorded_at")
    validate_timestamp_field(record.get("observed_at"), "observed_at")
    require_non_blank(record.get("producer_ref"), "producer_ref")
    validate_stable_ref(record.get("run_ref"), "run_ref")
    validate_supported_schema_version(record.get("schema_version"))
    record_type = require_allowed(record["record_type"], _RECORD_TYPES, "record_type")
    require_allowed(
        record.get("completeness_marker", "complete"),
        _COMPLETENESS_MARKERS,
        "completeness_marker",
    )
    require_allowed(
        record.get("degradation_marker", "none"),
        _DEGRADATION_MARKERS,
        "degradation_marker",
    )
    validate_optional_stable_ref(record.get("stage_execution_ref"), "stage_execution_ref")
    validate_optional_stable_ref(record.get("operation_context_ref"), "operation_context_ref")
    _validate_time_order(record)
    _validate_correlation_refs(cast(Mapping[str, Any], record.get("correlation_refs", {})))
    validate_record_payload(record_type, cast(Mapping[str, Any], record["payload"]))


def _validate_time_order(record: Mapping[str, Any]) -> None:
    recorded_at = record.get("recorded_at")
    observed_at = record.get("observed_at")
    if not isinstance(recorded_at, str) or not isinstance(observed_at, str):
        raise RecordValidationError("recorded_at and observed_at must be strings")
    if recorded_at < observed_at:
        raise RecordValidationError("recorded_at must be >= observed_at")


def _validate_correlation_refs(payload: Mapping[str, Any]) -> None:
    for key, value in payload.items():
        if not isinstance(key, str) or not key.strip():
            raise RecordValidationError(
                "correlation_refs must use non-blank string keys"
            )
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            raise RecordValidationError(
                "correlation_refs must use non-blank string values when present"
            )
