"""Deterministic physical-geometry revisions for runtime-data compatibility."""

from dataclasses import asdict, is_dataclass
from hashlib import sha256
import json
from typing import Any


def _canonical(value: Any) -> Any:
    """Convert frozen configuration objects into stable JSON-compatible values."""
    if is_dataclass(value):
        return _canonical(asdict(value))
    if isinstance(value, dict):
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


def geometry_revision(user_settings: object, commissioning: object) -> str:
    """Fingerprint the board, task frame, and pen vector that affect calibration."""
    payload = {
        'board': _canonical(user_settings.board),
        'task_reference_frame': commissioning.frames.task_reference_frame,
        'pen': _canonical(commissioning.calibration_pen),
        'runtime_schema': 1,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return sha256(serialized.encode('utf-8')).hexdigest()


def pen_transform_revision(commissioning: object) -> str:
    """Fingerprint only the pen transform used while capturing calibration points."""
    serialized = json.dumps(
        _canonical(commissioning.calibration_pen), sort_keys=True, separators=(',', ':')
    )
    return sha256(serialized.encode('utf-8')).hexdigest()
