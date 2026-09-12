"""Stable, hardware-neutral application contracts used by the game manager."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, Tuple

from .models import CubeKind, GameCoordinate, GridCell
from .state_machine import PhysicalProgress


class ExecutionOutcome(IntEnum):
    """Terminal result categories for an application pick-and-place request."""

    SUCCEEDED = 0
    CANCELED = 1
    FAILED = 2


class ExecutionErrorCode(IntEnum):
    """Stable failure codes that do not expose driver implementation details."""

    NONE = 0
    INVALID_STATE = 1
    STALE_ROUND = 2
    DUPLICATE_REQUEST = 3
    INVALID_SELECTION = 4
    PLANNING_FAILED = 10
    EXECUTION_FAILED = 11
    GRIPPER_FAILED = 12
    CANCELED = 13
    RECONCILIATION_REQUIRED = 14
    UNKNOWN = 255


@dataclass(frozen=True)
class OperationRequest:
    """Physical request independent from whether the selection is correct."""

    request_id: str
    operation_id: str
    round_id: str
    cube_id: str
    cell: GridCell
    destination_id: str
    destination_policy: str
    configuration_revision: str
    calibration_revision: str


@dataclass(frozen=True)
class ExecutionResult:
    """Structured motion outcome, including ambiguity for operator recovery."""

    operation_id: str
    outcome: ExecutionOutcome
    error_code: ExecutionErrorCode = ExecutionErrorCode.NONE
    error_summary: str = ''
    physical_progress: PhysicalProgress = PhysicalProgress.NOT_STARTED


@dataclass(frozen=True)
class SnapshotCube:
    """One visual/game cube in a complete application state snapshot."""

    cube_id: str
    kind: CubeKind
    cell: GridCell
    game_coordinate: GameCoordinate
    removed: bool


@dataclass(frozen=True)
class GameSnapshot:
    """Versioned state needed by a reconnecting UI or operator client."""

    schema_version: int
    state_version: int
    round_id: Optional[str]
    mode: Optional[str]
    game_state: str
    origin_cell: Optional[GridCell]
    rotation_deg: Optional[int]
    handedness: Optional[str]
    beginner_target_coordinate: Optional[GameCoordinate]
    cubes: Tuple[SnapshotCube, ...]
    answer_order: Tuple[str, ...]
    selected_answer_ids: Tuple[str, ...]
    disabled_answer_ids: Tuple[str, ...]
    attempts_remaining: int
    operation_state: str
    pending_request_id: Optional[str]
    pending_operation_id: Optional[str]
    game_flow_ready: bool
    error_code: ExecutionErrorCode
    error_summary: str
    error_recoverable: bool
    physical_progress: PhysicalProgress


@dataclass(frozen=True)
class IntentResult:
    """Idempotent result returned for an application intent request."""

    accepted: bool
    requires_motion: bool
    error_code: ExecutionErrorCode
    error_summary: str
    snapshot: GameSnapshot
