"""Operational logging helpers for Stream."""

from __future__ import annotations

import logging
from pathlib import Path


def get_logger() -> logging.Logger:
    logger = logging.getLogger("stream")
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


class OperationalLogger:
    """Structured log facade for Stream store lifecycle events."""

    def __init__(self) -> None:
        self._logger = get_logger()

    def store_opened(self, *, root_path: Path, durability_mode: str) -> None:
        self._logger.info(
            "component=store event=opened root_path=%s durability_mode=%s",
            root_path,
            durability_mode,
        )

    def append_completed(
        self, *, accepted_count: int, rejected_count: int, durability_status: str
    ) -> None:
        level = logging.WARNING if rejected_count else logging.DEBUG
        self._logger.log(
            level,
            "component=writer event=append_completed accepted=%s rejected=%s durability=%s",
            accepted_count,
            rejected_count,
            durability_status,
        )

    def segment_rolled(self, *, from_segment: int, to_segment: int) -> None:
        self._logger.info(
            "component=layout event=segment_rolled from=%s to=%s",
            from_segment,
            to_segment,
        )

    def integrity_checked(
        self, *, state: str, issue_count: int, record_count: int
    ) -> None:
        level = logging.WARNING if state != "healthy" else logging.INFO
        self._logger.log(
            level,
            "component=integrity event=checked state=%s issue_count=%s record_count=%s",
            state,
            issue_count,
            record_count,
        )

    def replay_completed(
        self, *, mode: str, record_count: int, gap_count: int
    ) -> None:
        level = logging.WARNING if gap_count else logging.INFO
        self._logger.log(
            level,
            "component=replay event=completed mode=%s record_count=%s gaps=%s",
            mode,
            record_count,
            gap_count,
        )

    def repair_completed(
        self, *, operation: str, success: bool, repaired_count: int
    ) -> None:
        level = logging.WARNING if not success else logging.INFO
        self._logger.log(
            level,
            "component=repair event=completed operation=%s success=%s repaired=%s",
            operation,
            str(success).lower(),
            repaired_count,
        )

    def export_completed(self, *, destination: Path, record_count: int) -> None:
        self._logger.info(
            "component=export event=completed destination=%s record_count=%s",
            destination,
            record_count,
        )
