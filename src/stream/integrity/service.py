"""Integrity checks for Stream layout and segments."""

from __future__ import annotations

import json

from ..exceptions import IntegrityError
from ..layout import LayoutManager
from ..models import IntegrityIssue, IntegrityReport, IntegrityState


class IntegrityChecker:
    """Inspect manifest and segments for append-order and corruption issues."""

    def __init__(self, layout: LayoutManager) -> None:
        self._layout = layout

    def check(self) -> IntegrityReport:
        try:
            manifest = self._layout.load_manifest()
            issues: list[IntegrityIssue] = []
            recommendations: list[str] = []
            expected_sequence = 1
            record_count = 0
            segment_ids = self._layout.iter_segment_ids()
            for segment_id in segment_ids:
                path = self._layout.segment_path(segment_id)
                with path.open("r", encoding="utf-8") as handle:
                    lines = handle.readlines()
                for line_number, line in enumerate(lines, start=1):
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        code = "invalid_json_line"
                        message = "segment line is not valid JSON"
                        if line_number == len(lines) and not line.endswith("\n"):
                            code = "truncated_line"
                            message = "last segment line looks truncated or partially written"
                        issues.append(
                            IntegrityIssue(
                                severity="error",
                                code=code,
                                message=message,
                                segment_id=segment_id,
                                line_number=line_number,
                            )
                        )
                        continue
                    sequence = int(entry.get("sequence", -1))
                    if sequence != expected_sequence:
                        issues.append(
                            IntegrityIssue(
                                severity="error",
                                code="sequence_gap",
                                message=(
                                    f"expected sequence {expected_sequence} "
                                    f"but found {sequence}"
                                ),
                                segment_id=segment_id,
                                line_number=line_number,
                            )
                        )
                        expected_sequence = sequence
                    expected_sequence += 1
                    record_count += 1
            manifest_next_sequence = int(manifest["next_sequence"])
            if manifest_next_sequence != expected_sequence:
                issues.append(
                    IntegrityIssue(
                        severity="warning",
                        code="manifest_sequence_mismatch",
                        message="manifest next_sequence does not match observed segment history",
                    )
                )
            if any(issue.code == "truncated_line" for issue in issues):
                recommendations.append(
                    "Run tolerant replay or repair the damaged segment tail before strict replay."
                )
            if any(issue.code == "sequence_gap" for issue in issues):
                recommendations.append(
                    "Inspect segment ordering and rebuild derivative indexes after repair."
                )
            state = _classify_state(issues)
            return IntegrityReport(
                healthy=state == IntegrityState.HEALTHY,
                issues=tuple(issues),
                segment_count=len(segment_ids),
                record_count=record_count,
                state=state,
                recommendations=tuple(recommendations),
            )
        except Exception as exc:  # pragma: no cover
            raise IntegrityError("integrity check failed") from exc


def _classify_state(issues: list[IntegrityIssue]) -> IntegrityState:
    if any(issue.severity == "error" for issue in issues):
        return IntegrityState.CORRUPTED
    if issues:
        return IntegrityState.DEGRADED
    return IntegrityState.HEALTHY
