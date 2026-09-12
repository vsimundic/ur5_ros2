"""Versioned, hardware-neutral schemas for generated application data."""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any, Mapping, Optional, Tuple

from .models import ConfigError


def _finite_vector(values: Tuple[float, ...], size: int, name: str) -> None:
    if len(values) != size or any(not isfinite(value) for value in values):
        raise ConfigError(f'{name} must contain {size} finite values')


@dataclass(frozen=True)
class FrameTaggedPose:
    """A Cartesian pose whose reference frame is always explicit."""

    frame_id: str
    translation_m: Tuple[float, float, float]
    rotation_xyzw: Tuple[float, float, float, float]

    def __post_init__(self) -> None:
        """Validate a finite pose with a non-empty frame identity."""
        if not self.frame_id.strip():
            raise ConfigError('frame_id must be a non-empty string')
        _finite_vector(self.translation_m, 3, 'translation_m')
        _finite_vector(self.rotation_xyzw, 4, 'rotation_xyzw')


@dataclass(frozen=True)
class CalibrationData:
    """Future grid calibration data; absent calibration remains valid state."""

    schema_version: int
    created_at: datetime
    task_reference_frame: str
    p0_m: Tuple[float, float, float]
    px_m: Tuple[float, float, float]
    py_m: Tuple[float, float, float]
    grid_pose: FrameTaggedPose
    configuration_revision: str
    quality: Mapping[str, float]
    pxy_error_m: Optional[float] = None

    def __post_init__(self) -> None:
        """Validate a complete accepted calibration record without measuring it."""
        if self.schema_version != 1:
            raise ConfigError('calibration schema_version must be 1')
        if self.task_reference_frame != 'base_link':
            raise ConfigError('calibration task_reference_frame must be base_link')
        for name, point in (('p0_m', self.p0_m), ('px_m', self.px_m), ('py_m', self.py_m)):
            _finite_vector(point, 3, name)
        if self.grid_pose.frame_id != self.task_reference_frame:
            raise ConfigError('grid_pose must be expressed in task_reference_frame')
        if not self.configuration_revision:
            raise ConfigError('configuration_revision is required')
        if any(not isfinite(value) for value in self.quality.values()):
            raise ConfigError('calibration quality values must be finite')
        if self.pxy_error_m is not None and (
            not isfinite(self.pxy_error_m) or self.pxy_error_m < 0.0
        ):
            raise ConfigError('pxy_error_m must be a finite non-negative value')


@dataclass(frozen=True)
class TaughtPoseData:
    """A future operator-taught pose with provenance and explicit frame."""

    schema_version: int
    name: str
    created_at: datetime
    pose: FrameTaggedPose
    configuration_revision: str
    calibration_revision: Optional[str]

    def __post_init__(self) -> None:
        """Validate identity and revision fields without supplying positions."""
        if self.schema_version != 1 or not self.name or not self.configuration_revision:
            raise ConfigError(
                'taught pose requires schema version, name, and configuration revision'
            )


@dataclass(frozen=True)
class EventRecord:
    """One append-only JSONL application event."""

    schema_version: int
    timestamp: datetime
    event_type: str
    state_version: int
    round_id: Optional[str]
    request_id: Optional[str]
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        """Reject ambiguous identities and invalid sequence numbers."""
        if self.schema_version != 1 or not self.event_type:
            raise ConfigError('event requires schema version and event_type')
        if self.state_version < 0:
            raise ConfigError('event state_version must be non-negative')
