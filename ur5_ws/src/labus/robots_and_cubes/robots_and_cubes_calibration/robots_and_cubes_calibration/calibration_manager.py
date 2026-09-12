"""Command-free, transactional grid-calibration lifecycle."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from time import time
from typing import Callable, Dict, Optional, Tuple
from uuid import uuid4

from .geometry import (
    calibrate,
    CalibrationGeometryError,
    fourth_point_error,
    GridTransform,
    Matrix,
    Metrics,
    pen_tip,
    Vector,
)


class CalibrationState(str, Enum):
    """The state of the current candidate, independent of active calibration."""

    NOT_AVAILABLE = 'not_available'
    DRAFT_STARTED = 'draft_started'
    P0_CAPTURED = 'p0_captured'
    PX_CAPTURED = 'px_captured'
    PY_CAPTURED = 'py_captured'
    VALIDATED = 'validated'
    INVALID = 'invalid'
    ACCEPTED = 'accepted'


@dataclass(frozen=True)
class MeasuredToolPose:
    """A fresh measured ``base_link -> tool0`` pose supplied by an adapter."""

    translation_m: Vector
    rotation_matrix: Matrix
    stamp_seconds: float
    source: str = 'measured_tf'


@dataclass(frozen=True)
class AcceptedCalibration:
    """The complete persisted result of an explicitly accepted calibration."""

    calibration_id: str
    revision: int
    accepted_at: str
    parent_frame: str
    child_frame: str
    p0_m: Vector
    px_m: Vector
    py_m: Vector
    pxy_m: Optional[Vector]
    transform: GridTransform
    metrics: Metrics
    fourth_point_error_m: Optional[float]
    geometry_revision: str
    pen_transform_revision: str


@dataclass(frozen=True)
class CalibrationStatus:
    """UI-safe lifecycle status, including the active-calibration condition."""

    state: CalibrationState
    active_valid: bool
    reason: Optional[str]
    captured_points: Tuple[str, ...]
    active_calibration_id: Optional[str]


class CalibrationManager:
    """Build candidates separately so a failed recalibration cannot erase the active one."""

    def __init__(
        self,
        settings: object,
        pen_offset: Vector,
        geometry_revision: str,
        pen_transform_revision: str,
        clock: Callable[[], float] = time,
        event_logger: object | None = None,
    ) -> None:
        self.settings = settings
        self.pen_offset = tuple(pen_offset)
        self.geometry_revision = geometry_revision
        self.pen_transform_revision = pen_transform_revision
        self.clock = clock
        self.event_logger = event_logger
        self.state = CalibrationState.NOT_AVAILABLE
        self._draft: Dict[str, Vector] = {}
        self._candidate: Optional[AcceptedCalibration] = None
        self.accepted: Optional[AcceptedCalibration] = None
        self._reason: Optional[str] = None

    def _event(self, event_type: str, payload: dict) -> None:
        """Best-effort event integration; logging may never change calibration state."""
        if self.event_logger is not None:
            try:
                self.event_logger.write(event_type, 0, None, None, payload)
            except (AttributeError, OSError, ValueError):
                pass

    def status(self) -> CalibrationStatus:
        """Return candidate and active-calibration status without exposing mutable state."""
        return CalibrationStatus(
            state=self.state,
            active_valid=self.accepted is not None,
            reason=self._reason,
            captured_points=tuple(sorted(self._draft)),
            active_calibration_id=(self.accepted.calibration_id if self.accepted else None),
        )

    def start(self) -> CalibrationStatus:
        """Start a new candidate while retaining any previously accepted transform."""
        self._draft = {}
        self._candidate = None
        self._reason = None
        self.state = CalibrationState.DRAFT_STARTED
        self._event('calibration_started', {})
        return self.status()

    def capture(self, name: str, pose: MeasuredToolPose) -> CalibrationStatus:
        """Capture a named pen-tip point from a fresh measured tool transform."""
        if self.state not in {
            CalibrationState.DRAFT_STARTED,
            CalibrationState.P0_CAPTURED,
            CalibrationState.PX_CAPTURED,
            CalibrationState.PY_CAPTURED,
            CalibrationState.INVALID,
        }:
            raise CalibrationGeometryError('calibration draft is not active')
        if name not in ('P0', 'PX', 'PY', 'PXY'):
            raise CalibrationGeometryError('unknown calibration point')
        maximum_age = self.settings.calibration.maximum_capture_age_seconds
        if self.clock() - pose.stamp_seconds > maximum_age:
            raise CalibrationGeometryError('measured tool pose is stale')
        self._draft[name] = pen_tip(
            pose.translation_m, pose.rotation_matrix, self.pen_offset
        )
        self._candidate = None
        self._reason = None
        self.state = {
            'P0': CalibrationState.P0_CAPTURED,
            'PX': CalibrationState.PX_CAPTURED,
            'PY': CalibrationState.PY_CAPTURED,
        }.get(name, self.state)
        self._event('calibration_point_captured', {'point': name, 'source': pose.source})
        return self.status()

    def validate(self) -> AcceptedCalibration:
        """Validate P0/PX/PY and optional PXY without replacing the active result."""
        try:
            board = self.settings.board
            transform, metrics = calibrate(
                self._draft['P0'],
                self._draft['PX'],
                self._draft['PY'],
                board.columns * board.cell_size_m,
                board.rows * board.cell_size_m,
                self.settings.calibration.maximum_side_length_error_m,
                self.settings.calibration.maximum_angle_error_deg,
                self.settings.calibration.minimum_vector_length_m,
            )
            pxy_error = None
            if 'PXY' in self._draft:
                pxy_error = fourth_point_error(
                    transform,
                    board.columns * board.cell_size_m,
                    board.rows * board.cell_size_m,
                    self._draft['PXY'],
                )
                if pxy_error > self.settings.calibration.maximum_fourth_point_error_m:
                    raise CalibrationGeometryError('fourth point exceeds configured tolerance')
            next_revision = 1 if self.accepted is None else self.accepted.revision + 1
            self._candidate = AcceptedCalibration(
                calibration_id=str(uuid4()),
                revision=next_revision,
                accepted_at=datetime.now(timezone.utc).isoformat(),
                parent_frame='base_link',
                child_frame='grid_frame',
                p0_m=self._draft['P0'],
                px_m=self._draft['PX'],
                py_m=self._draft['PY'],
                pxy_m=self._draft.get('PXY'),
                transform=transform,
                metrics=metrics,
                fourth_point_error_m=pxy_error,
                geometry_revision=self.geometry_revision,
                pen_transform_revision=self.pen_transform_revision,
            )
        except (KeyError, CalibrationGeometryError) as error:
            self._candidate = None
            self._reason = str(error)
            self.state = CalibrationState.INVALID
            self._event('calibration_validation_failed', {'reason': self._reason})
            raise CalibrationGeometryError(self._reason) from error
        self._reason = None
        self.state = CalibrationState.VALIDATED
        return self._candidate

    def accept(
        self, persist: Callable[[AcceptedCalibration], None] | None = None
    ) -> AcceptedCalibration:
        """Persist a candidate, then switch the active value only if persistence succeeds."""
        if self.state is not CalibrationState.VALIDATED or self._candidate is None:
            raise CalibrationGeometryError('calibration is not validated')
        if persist is not None:
            persist(self._candidate)
        self.accepted = self._candidate
        self._candidate = None
        self._draft = {}
        self.state = CalibrationState.ACCEPTED
        self._reason = None
        self._event('calibration_accepted', {'id': self.accepted.calibration_id})
        return self.accepted

    def cancel(self) -> CalibrationStatus:
        """Discard only the candidate and leave the last accepted calibration active."""
        self._draft = {}
        self._candidate = None
        self._reason = None
        self.state = CalibrationState.ACCEPTED if self.accepted else CalibrationState.NOT_AVAILABLE
        self._event('calibration_canceled', {})
        return self.status()

    def restore(self, calibration: AcceptedCalibration) -> CalibrationStatus:
        """Install a fully validated compatible record loaded from runtime storage."""
        if calibration.geometry_revision != self.geometry_revision:
            return self.invalidate('calibration geometry revision is incompatible')
        if calibration.pen_transform_revision != self.pen_transform_revision:
            return self.invalidate('calibration pen transform revision is incompatible')
        if calibration.parent_frame != 'base_link' or calibration.child_frame != 'grid_frame':
            return self.invalidate('calibration frame convention is incompatible')
        self.accepted = calibration
        self._candidate = None
        self._draft = {}
        self._reason = None
        self.state = CalibrationState.ACCEPTED
        return self.status()

    def invalidate(self, reason: str) -> CalibrationStatus:
        """Mark an incompatible loaded result unavailable and expose its reason."""
        self.accepted = None
        self._candidate = None
        self._draft = {}
        self._reason = reason
        self.state = CalibrationState.INVALID
        self._event('calibration_invalidated', {'reason': reason})
        return self.status()
