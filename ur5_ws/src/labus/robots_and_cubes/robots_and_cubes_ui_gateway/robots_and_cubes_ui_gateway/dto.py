"""Explicit, browser-safe application data transfer objects."""

from dataclasses import asdict, dataclass
from typing import Any, Optional


MODE_NAMES = ('easy', 'beginner', 'standard', 'challenge', 'spatial')
HAND_NAMES = ('right', 'left')
STAGE_NAMES = (
    'planning', 'moving_to_pregrasp', 'descending', 'grasping', 'lifting',
    'moving_to_destination', 'releasing', 'retreating',
)
OPERATION_NAMES = ('idle', 'executing', 'reconciliation_required')
VISUAL_KINDS = ('red', 'green', 'blue', 'black', 'white')
SHAPE_SYMBOLS = {
    'green': '★', 'blue': '●', 'red': '♥', 'black': '▲', 'white': '☾',
}


@dataclass(frozen=True)
class BrowserCube:
    """A visual cube and its already-calculated educational coordinate."""

    id: str  # noqa: A003 - browser contract deliberately uses the conventional id field.
    visual_kind: str
    symbol: str
    column: int
    row: int
    game_coordinate: dict[str, int]
    removed: bool


@dataclass(frozen=True)
class BrowserSnapshot:
    """A complete snapshot without ROS graph, controller, or action internals."""

    schema_version: int
    version: int
    round_id: Optional[str]
    mode: Optional[str]
    game_state: str
    board: dict[str, int]
    origin: Optional[dict[str, Any]]
    target_visual_kind: Optional[str]
    target_coordinate: Optional[dict[str, int]]
    cubes: tuple[BrowserCube, ...]
    answer_order: tuple[str, ...]
    selected_answer_ids: tuple[str, ...]
    disabled_answer_ids: tuple[str, ...]
    attempts_remaining: int
    readiness: dict[str, bool]
    motion_stage: Optional[str]
    operation: dict[str, Optional[str]]
    recoverable_error: Optional[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Convert nested immutable DTOs to JSON-compatible application data."""
        return asdict(self)


@dataclass(frozen=True)
class BrowserIntentResult:
    """A response for an allowlisted application intent."""

    accepted: bool
    snapshot: BrowserSnapshot
    requires_motion: bool = False
    error: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Return a browser response without raw ROS response objects."""
        return {
            'accepted': self.accepted,
            'requires_motion': self.requires_motion,
            'error': self.error,
            'snapshot': self.snapshot.to_dict(),
        }


def snapshot_from_ros(message: object, rows: int, columns: int) -> BrowserSnapshot:
    """Project the allowlisted fields of a ``GameStateSnapshot`` ROS message."""
    mode = MODE_NAMES[message.mode] if 0 <= message.mode < len(MODE_NAMES) else None

    def visual_kind(value: int) -> str:
        return VISUAL_KINDS[value] if 0 <= value < len(VISUAL_KINDS) else 'black'

    cubes = tuple(
        BrowserCube(
            id=cube.cube_id,
            visual_kind=visual_kind(cube.visual_kind),
            symbol=(
                '■' if mode == 'easy'
                else SHAPE_SYMBOLS[visual_kind(cube.visual_kind)]
            ),
            column=cube.column,
            row=cube.row,
            game_coordinate={'x': cube.game_x, 'y': cube.game_y},
            removed=cube.removed,
        )
        for cube in message.cubes
    )
    error = message.recoverable_error
    has_error = bool(error.code or error.summary)
    origin = None if not message.has_origin else {
        'column': message.origin_column,
        'row': message.origin_row,
        'rotation_deg': message.rotation_deg,
        'handedness': HAND_NAMES[message.handedness]
        if 0 <= message.handedness < len(HAND_NAMES) else 'right',
    }
    stage = None
    operation_state = OPERATION_NAMES[message.robot_operation_state]
    if operation_state == 'executing' and 0 <= message.motion_stage < len(STAGE_NAMES):
        stage = STAGE_NAMES[message.motion_stage]
    return BrowserSnapshot(
        schema_version=message.schema_version,
        version=message.state_version,
        round_id=message.round_id or None,
        mode=mode,
        game_state=message.game_state,
        board={'rows': rows, 'columns': columns},
        origin=origin,
        target_visual_kind=(
            visual_kind(message.target_visual_kind)
            if message.has_target_visual_kind else None
        ),
        target_coordinate=(
            {'x': message.target_game_x, 'y': message.target_game_y}
            if message.has_target_coordinate else None
        ),
        cubes=cubes,
        answer_order=tuple(message.answer_order),
        selected_answer_ids=tuple(message.selected_answer_ids),
        disabled_answer_ids=tuple(message.disabled_answer_ids),
        attempts_remaining=message.attempts_remaining,
        readiness={'game_flow_ready': message.game_flow_ready},
        motion_stage=stage,
        operation={
            'state': operation_state,
            'request_id': message.pending_request_id or None,
            'id': message.pending_operation_id or None,
        },
        recoverable_error=None if not has_error else {
            'code': int(error.code),
            'summary': error.summary,
            'recoverable': error.recoverable,
            'physical_progress': int(error.physical_progress),
        },
    )


def intent_from_ros(response: object, rows: int, columns: int) -> BrowserIntentResult:
    """Project a game service result into the browser application model."""
    error = response.error
    return BrowserIntentResult(
        accepted=response.accepted,
        requires_motion=getattr(response, 'requires_motion', False),
        error=None if not error.code and not error.summary else {
            'code': int(error.code),
            'summary': error.summary,
            'recoverable': error.recoverable,
            'physical_progress': int(error.physical_progress),
        },
        snapshot=snapshot_from_ros(response.snapshot, rows, columns),
    )
