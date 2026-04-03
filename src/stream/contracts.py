"""Contract helpers for canonical Stream records."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from spine.models.common import SCHEMA_VERSION, normalize_timestamp

from .exceptions import RecordValidationError

SUPPORTED_SCHEMA_VERSIONS = frozenset({SCHEMA_VERSION})
CANONICAL_REF_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")


def validate_supported_schema_version(value: Any) -> str:
    """Validate the canonical schema version supported by this Stream build."""
    if not isinstance(value, str) or not value.strip():
        raise RecordValidationError("schema_version must be a non-blank string")
    if value not in SUPPORTED_SCHEMA_VERSIONS:
        raise RecordValidationError(f"unsupported schema_version: {value}")
    return value


def validate_timestamp_field(value: Any, field_name: str) -> str:
    """Validate and normalize a canonical timestamp field."""
    if not isinstance(value, str) or not value.strip():
        raise RecordValidationError(f"{field_name} must be a non-blank string")
    try:
        normalized = normalize_timestamp(value)
    except ValueError as exc:
        raise RecordValidationError(
            f"{field_name} must be an ISO-8601 UTC timestamp with trailing Z"
        ) from exc
    if normalized != value:
        raise RecordValidationError(
            f"{field_name} must already be normalized to ISO-8601 UTC with trailing Z"
        )
    return value


def validate_stable_ref(value: Any, field_name: str) -> str:
    """Validate a stable reference string used inside canonical records."""
    if not isinstance(value, str) or not value.strip():
        raise RecordValidationError(f"{field_name} must be a non-blank string")
    if not CANONICAL_REF_PATTERN.fullmatch(value):
        raise RecordValidationError(
            f"{field_name} must be a canonical reference string"
        )
    return value


def validate_optional_stable_ref(value: Any, field_name: str) -> str | None:
    """Validate an optional stable reference."""
    if value is None:
        return None
    return validate_stable_ref(value, field_name)


def validate_string_mapping(
    value: Any,
    field_name: str,
    *,
    allow_any_values: bool = False,
) -> Mapping[str, Any]:
    """Validate a mapping with string keys and optionally string values."""
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise RecordValidationError(f"{field_name} must be a mapping")
    normalized: dict[str, Any] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            raise RecordValidationError(f"{field_name} must use non-blank string keys")
        if not allow_any_values and (
            not isinstance(raw_value, str) or not raw_value.strip()
        ):
            raise RecordValidationError(
                f"{field_name} must use non-blank string values"
            )
        normalized[raw_key] = raw_value
    return normalized
