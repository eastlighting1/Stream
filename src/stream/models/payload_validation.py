"""Record-type specific payload validators for canonical Stream records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..contracts import validate_optional_stable_ref, validate_string_mapping
from ..exceptions import RecordValidationError

_EVENT_LEVELS = frozenset({"debug", "info", "warning", "error", "critical"})
_METRIC_VALUE_TYPES = frozenset({"scalar", "integer", "float"})
_METRIC_SCOPES = frozenset(
    {"global", "run", "stage", "operation", "step", "batch", "epoch", "dataset"}
)
_TRACE_STATUSES = frozenset({"ok", "error", "cancelled", "timeout"})
_TRACE_KINDS = frozenset(
    {"internal", "client", "server", "producer", "consumer", "model_call"}
)


def validate_record_payload(record_type: str, payload: Mapping[str, Any]) -> None:
    if record_type == "structured_event":
        _validate_structured_event_payload(payload)
    elif record_type == "metric":
        _validate_metric_payload(payload)
    elif record_type == "trace_span":
        _validate_trace_span_payload(payload)
    else:
        _validate_degradation_payload(payload)


def require_non_blank(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise RecordValidationError(f"{field_name} must be a non-blank string")


def require_allowed(value: Any, allowed: frozenset[str], field_name: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise RecordValidationError(f"{field_name} must be one of: {', '.join(sorted(allowed))}")
    return value


def validate_string_sequence(value: Any, field_name: str) -> None:
    if value is None:
        return
    if not isinstance(value, (list, tuple)):
        raise RecordValidationError(f"{field_name} must be a list or tuple of strings")
    for item in value:
        require_non_blank(item, field_name)


def _validate_structured_event_payload(payload: Mapping[str, Any]) -> None:
    require_non_blank(payload.get("event_key"), "payload.event_key")
    require_allowed(payload.get("level"), _EVENT_LEVELS, "payload.level")
    require_non_blank(payload.get("message"), "payload.message")
    validate_optional_stable_ref(payload.get("subject_ref"), "payload.subject_ref")
    validate_string_mapping(
        payload.get("attributes", {}),
        "payload.attributes",
        allow_any_values=True,
    )


def _validate_metric_payload(payload: Mapping[str, Any]) -> None:
    require_non_blank(payload.get("metric_key"), "payload.metric_key")
    require_allowed(payload.get("value_type"), _METRIC_VALUE_TYPES, "payload.value_type")
    require_allowed(
        payload.get("aggregation_scope", "step"),
        _METRIC_SCOPES,
        "payload.aggregation_scope",
    )
    value = payload.get("value")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise RecordValidationError("payload.value must be numeric")
    validate_optional_stable_ref(payload.get("subject_ref"), "payload.subject_ref")
    validate_optional_stable_ref(payload.get("slice_ref"), "payload.slice_ref")
    validate_string_mapping(payload.get("tags", {}), "payload.tags", allow_any_values=False)


def _validate_trace_span_payload(payload: Mapping[str, Any]) -> None:
    from ..contracts import validate_timestamp_field

    require_non_blank(payload.get("span_id"), "payload.span_id")
    require_non_blank(payload.get("trace_id"), "payload.trace_id")
    require_non_blank(payload.get("span_name"), "payload.span_name")
    require_allowed(payload.get("status"), _TRACE_STATUSES, "payload.status")
    require_allowed(payload.get("span_kind"), _TRACE_KINDS, "payload.span_kind")
    validate_timestamp_field(payload.get("started_at"), "payload.started_at")
    validate_timestamp_field(payload.get("ended_at"), "payload.ended_at")
    validate_string_mapping(
        payload.get("attributes", {}),
        "payload.attributes",
        allow_any_values=True,
    )
    validate_string_sequence(payload.get("linked_refs", ()), "payload.linked_refs")


def _validate_degradation_payload(payload: Mapping[str, Any]) -> None:
    require_non_blank(payload.get("reason"), "payload.reason")
    require_non_blank(payload.get("status"), "payload.status")
