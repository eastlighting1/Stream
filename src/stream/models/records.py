"""Canonical record normalization entry points."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from typing import Any, cast

from ..exceptions import RecordValidationError
from .canonical_validation import normalize_mapping_record, validate_mapping_record
from .spine_adapter import is_supported_spine_record, normalize_spine_record


def normalize_record(record: object) -> dict[str, Any]:
    """Normalize a supported record object into a JSON-ready canonical mapping."""
    if is_supported_spine_record(record):
        try:
            normalized = normalize_spine_record(record)
        except ValueError as exc:
            raise RecordValidationError(str(exc)) from exc
        validate_mapping_record(normalized)
        return normalized
    if isinstance(record, Mapping):
        normalized = normalize_mapping_record(record)
        validate_mapping_record(normalized)
        return normalized
    if is_dataclass(record):
        return normalize_record(cast(object, asdict(cast(Any, record))))
    raise RecordValidationError(f"unsupported record type: {type(record).__name__}")
