"""Export services built on top of replayable canonical history."""

from __future__ import annotations

import json
from pathlib import Path

from ..models import ReplayMode, ReplayResult, ScanFilter
from ..replay import ReplayService


class ExportService:
    """Export canonical record history without redefining stored truth."""

    def __init__(self, replay: ReplayService) -> None:
        self._replay = replay

    def export_jsonl(
        self,
        destination: Path,
        scan_filter: ScanFilter | None = None,
        *,
        mode: ReplayMode = ReplayMode.STRICT,
    ) -> ReplayResult:
        replay_result = self._replay.replay(scan_filter, mode=mode)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8", newline="\n") as handle:
            for stored in replay_result.records:
                handle.write(json.dumps(stored.record, sort_keys=True) + "\n")
        return replay_result
