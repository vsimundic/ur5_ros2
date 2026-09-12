"""Best-effort JSONL event logging for application-level events."""

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from robots_and_cubes_config.runtime import EventRecord


class JsonlEventLogger:
    """Append structured events without allowing logging failures to affect play."""

    def __init__(self, path: Path) -> None:
        """Use an explicit operator-managed JSONL path."""
        self._path = path

    def write(
        self,
        event_type: str,
        state_version: int,
        round_id: str | None,
        request_id: str | None,
        payload: Mapping[str, Any],
    ) -> None:
        """Append one serializable record and suppress filesystem failures."""
        record = EventRecord(
            schema_version=1,
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            state_version=state_version,
            round_id=round_id,
            request_id=request_id,
            payload=dict(payload),
        )
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(asdict(record), default=str, sort_keys=True))
                stream.write('\n')
        except OSError:
            return
