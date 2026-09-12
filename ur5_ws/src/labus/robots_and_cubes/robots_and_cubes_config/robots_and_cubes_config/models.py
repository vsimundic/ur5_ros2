"""Typed, immutable Robots and Cubes configuration models."""

from dataclasses import dataclass
from typing import Optional, Tuple


SUPPORTED_MODES = ('easy', 'beginner', 'standard', 'challenge')
SUPPORTED_ROTATIONS = (0, 90, 180, 270)
MAX_TOUCHSCREEN_ANSWERS = 12


class ConfigError(ValueError):
    """A configuration value is missing, unknown, or inconsistent."""


@dataclass(frozen=True)
class CubeCounts:
    """Configured red and green cube quantities."""

    red_count: int
    green_count: int

    @property
    def total(self) -> int:
        """Return the total cube count."""
        return self.red_count + self.green_count


@dataclass(frozen=True)
class StandardSettings:
    """Standard-mode origin restrictions."""

    central_origin_margin_cells: int


@dataclass(frozen=True)
class ChallengeSettings:
    """Enabled Challenge orientations and handedness."""

    rotations_deg: Tuple[int, ...]
    enable_left_handed: bool


@dataclass(frozen=True)
class GameSettings:
    """Mode, attempt, and cube settings."""

    enabled_modes: Tuple[str, ...]
    attempts: int
    cubes: CubeCounts
    standard: StandardSettings
    challenge: ChallengeSettings


@dataclass(frozen=True)
class BoardSettings:
    """Physical grid dimensions and cell pitch."""

    rows: int
    columns: int
    cell_size_m: float

    @property
    def cell_count(self) -> int:
        """Return the number of board cells."""
        return self.rows * self.columns


@dataclass(frozen=True)
class Size3D:
    """Three-dimensional size in metres."""

    x: float
    y: float
    z: float


@dataclass(frozen=True)
class CubeSettings:
    """Physical cube geometry."""

    size_m: Size3D


@dataclass(frozen=True)
class GenerationSettings:
    """Round-generation constraints and bounded-search policy."""

    allow_adjacent_cubes: bool
    minimum_cell_distance: int
    favor_coordinate_sign_variety: bool
    require_positive_x: bool
    require_negative_x: bool
    require_positive_y: bool
    require_negative_y: bool
    maximum_attempts: int


@dataclass(frozen=True)
class MockSettings:
    """Hardware-free timing settings reserved for mock execution."""

    movement_duration_seconds: float


@dataclass(frozen=True)
class UserSettings:
    """Fully validated normal user configuration."""

    schema_version: int
    application_name: str
    game: GameSettings
    board: BoardSettings
    cube: CubeSettings
    generation: GenerationSettings
    mock: MockSettings


@dataclass(frozen=True)
class RobotIdentity:
    """Discovered robot and MoveIt identifiers."""

    base_frame: str
    planning_frame: str
    planning_group: str
    planning_end_link: str


@dataclass(frozen=True)
class RigidTransform:
    """Translation and unit-quaternion rigid transform."""

    translation_m: Tuple[float, float, float]
    rotation_xyzw: Tuple[float, float, float, float]


@dataclass(frozen=True)
class JointLimit:
    """Commissioned range for one named joint."""

    joint_name: str
    minimum_rad: float
    maximum_rad: float


@dataclass(frozen=True)
class MotionCommissioning:
    """Advanced motion values that remain unset until commissioning."""

    primary_pipeline: Optional[str]
    fallback_pipeline: Optional[str]
    fallback_planner_id: Optional[str]
    task_tcp_frame: Optional[str]
    tool_to_pen_tip: Optional[RigidTransform]
    allowed_joint_ranges_rad: Optional[Tuple[JointLimit, ...]]
    maximum_joint_excursion_rad: Optional[Tuple[Tuple[str, float], ...]]
    default_grasp_yaw_deg: Optional[float]


@dataclass(frozen=True)
class GripperCommissioning:
    """Known interface names and commissioned cube-grasp values."""

    command_action: str
    status_topic: str
    open_position_m: Optional[float]
    cube_close_position_m: Optional[float]
    cube_effort_n: Optional[float]


@dataclass(frozen=True)
class RobotCommissioning:
    """Validated advanced configuration with explicit readiness state."""

    schema_version: int
    robot: RobotIdentity
    motion: MotionCommissioning
    gripper: GripperCommissioning

    @property
    def real_execution_ready(self) -> bool:
        """Return whether every required physical value has been supplied."""
        motion_values = (
            self.motion.primary_pipeline,
            self.motion.task_tcp_frame,
            self.motion.tool_to_pen_tip,
            self.motion.allowed_joint_ranges_rad,
            self.motion.maximum_joint_excursion_rad,
            self.motion.default_grasp_yaw_deg,
        )
        gripper_values = (
            self.gripper.open_position_m,
            self.gripper.cube_close_position_m,
            self.gripper.cube_effort_n,
        )
        return all(value is not None for value in motion_values + gripper_values)
