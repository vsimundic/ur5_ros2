"""Explicit game state machine, independent of robot execution."""

from enum import Enum, IntEnum
from typing import Optional

from .models import GameRound


class GameState(str, Enum):
    """Explicit application states from startup through recovery."""

    STARTUP = 'startup'
    IDLE = 'idle'
    ROUND_GENERATED = 'round_generated'
    WAITING_FOR_PHYSICAL_SETUP = 'waiting_for_physical_setup'
    ROUND_PREFLIGHT = 'round_preflight'
    WAITING_FOR_CHILD = 'waiting_for_child'
    EXECUTING_SELECTION = 'executing_selection'
    SUCCESS = 'success'
    FAILED = 'failed'
    ROBOT_ERROR = 'robot_error'
    ABORTING = 'aborting'
    CALIBRATION = 'calibration'
    TEACHING_POSITION = 'teaching_position'


class SelectionDisposition(str, Enum):
    """A child selection is dispatched only after the UI locks input."""

    EXECUTION_REQUIRED = 'execution_required'


class PhysicalProgress(IntEnum):
    """Most advanced physical effect reported for a failed operation."""

    NOT_STARTED = 0
    PLANNING = 1
    MAY_HAVE_GRASPED = 2
    MAY_HAVE_TRANSPORTED = 3
    MAY_HAVE_RELEASED = 4


class InvalidTransition(RuntimeError):
    """The requested event is not valid in the current state."""


class GameStateMachine:
    """Own round progress while keeping motion success separate from correctness."""

    def __init__(self) -> None:
        """Initialize with no active round or execution request."""
        self.state = GameState.STARTUP
        self.round: Optional[GameRound] = None
        self.attempts_remaining = 0
        self.selected_answers: set[str] = set()
        self.removed_cubes: set[str] = set()
        self.pending_cube_id: Optional[str] = None
        self.pending_operation_id: Optional[str] = None
        self.physical_progress = PhysicalProgress.NOT_STARTED
        self.last_robot_error: Optional[str] = None

    def ready(self) -> None:
        """Complete non-motion startup and enter idle."""
        self._require(GameState.STARTUP)
        self.state = GameState.IDLE

    def start_calibration(self) -> None:
        """Enter the software calibration workflow from idle."""
        self._require(GameState.IDLE)
        self.state = GameState.CALIBRATION

    def start_teaching_position(self) -> None:
        """Enter the software position-teaching workflow from idle."""
        self._require(GameState.IDLE)
        self.state = GameState.TEACHING_POSITION

    def finish_operator_workflow(self) -> None:
        """Return from calibration or teaching without implying robot motion."""
        if self.state not in (GameState.CALIBRATION, GameState.TEACHING_POSITION):
            raise InvalidTransition('no operator workflow is active')
        self.state = GameState.IDLE

    def set_round(self, game_round: GameRound) -> None:
        """Install a generated round while idle."""
        self._require(GameState.IDLE)
        self.round = game_round
        self.attempts_remaining = game_round.attempts
        self.selected_answers.clear()
        self.removed_cubes.clear()
        self.pending_cube_id = None
        self.pending_operation_id = None
        self.physical_progress = PhysicalProgress.NOT_STARTED
        self.last_robot_error = None
        self.state = GameState.ROUND_GENERATED

    def request_physical_setup(self) -> None:
        """Move the generated round to operator setup."""
        self._require(GameState.ROUND_GENERATED)
        self.state = GameState.WAITING_FOR_PHYSICAL_SETUP

    def confirm_physical_setup(self) -> None:
        """Record operator confirmation and require preflight next."""
        self._require(GameState.WAITING_FOR_PHYSICAL_SETUP)
        self.state = GameState.ROUND_PREFLIGHT

    def complete_preflight(self, valid: bool, error: str = 'PREFLIGHT_FAILED') -> None:
        """Unlock child input only after a valid preflight result."""
        self._require(GameState.ROUND_PREFLIGHT)
        if valid:
            self.state = GameState.WAITING_FOR_CHILD
        else:
            self.last_robot_error = error
            self.state = GameState.ROBOT_ERROR

    def submit_selection(
        self, cube_id: str, operation_id: Optional[str] = None
    ) -> SelectionDisposition:
        """Accept one available child selection and lock input if needed."""
        self._require(GameState.WAITING_FOR_CHILD)
        game_round = self._round()
        cube = game_round.cube(cube_id)
        if cube_id in self.selected_answers or cube_id in self.removed_cubes:
            raise ValueError(f'cube is no longer selectable: {cube_id}')
        self.pending_cube_id = cube.cube_id
        self.pending_operation_id = operation_id
        self.physical_progress = PhysicalProgress.NOT_STARTED
        self.state = GameState.EXECUTING_SELECTION
        return SelectionDisposition.EXECUTION_REQUIRED

    def complete_motion(
        self,
        succeeded: bool,
        error: str = 'ROBOT_OPERATION_FAILED',
        physical_progress: PhysicalProgress = PhysicalProgress.NOT_STARTED,
    ) -> None:
        """Apply an execution result separately from game correctness."""
        self._require(GameState.EXECUTING_SELECTION)
        game_round = self._round()
        cube_id = self._pending()
        if not succeeded:
            if not isinstance(physical_progress, PhysicalProgress):
                raise TypeError('physical_progress must be PhysicalProgress')
            self.last_robot_error = error
            self.physical_progress = physical_progress
            self.state = GameState.ROBOT_ERROR
            return

        self.selected_answers.add(cube_id)
        self.removed_cubes.add(cube_id)
        self.pending_cube_id = None
        self.pending_operation_id = None
        self.physical_progress = PhysicalProgress.NOT_STARTED
        self.last_robot_error = None
        if game_round.is_correct(cube_id):
            self.state = GameState.SUCCESS
            return
        self.attempts_remaining -= 1
        self.state = (
            GameState.WAITING_FOR_CHILD
            if self.attempts_remaining > 0
            else GameState.FAILED
        )

    def retry_motion(self) -> None:
        """Retry the retained selection without consuming an attempt."""
        self._require(GameState.ROBOT_ERROR)
        if self.pending_cube_id is None:
            raise InvalidTransition('there is no failed selection to retry')
        if self.physical_progress >= PhysicalProgress.MAY_HAVE_GRASPED:
            raise InvalidTransition('operator reconciliation is required before retry')
        self.last_robot_error = None
        self.state = GameState.EXECUTING_SELECTION

    def confirm_retry_safe_after_reconciliation(self) -> None:
        """Allow retry only after an operator confirms no physical change remains."""
        self._require(GameState.ROBOT_ERROR)
        self._pending()
        if self.physical_progress < PhysicalProgress.MAY_HAVE_GRASPED:
            raise InvalidTransition('reconciliation is not required for this operation')
        self.physical_progress = PhysicalProgress.NOT_STARTED

    def begin_abort(self) -> None:
        """Enter aborting from any active application workflow."""
        if self.state in (GameState.STARTUP, GameState.IDLE, GameState.ABORTING):
            raise InvalidTransition(f'cannot abort from {self.state.value}')
        self.state = GameState.ABORTING

    def finish_abort(self) -> None:
        """Clear the active round after external abort work completes."""
        self._require(GameState.ABORTING)
        self.round = None
        self.attempts_remaining = 0
        self.selected_answers.clear()
        self.removed_cubes.clear()
        self.pending_cube_id = None
        self.pending_operation_id = None
        self.physical_progress = PhysicalProgress.NOT_STARTED
        self.last_robot_error = None
        self.state = GameState.IDLE

    def _round(self) -> GameRound:
        if self.round is None:
            raise InvalidTransition('no active round')
        return self.round

    def _pending(self) -> str:
        if self.pending_cube_id is None:
            raise InvalidTransition('no pending selection')
        return self.pending_cube_id

    def _require(self, expected: GameState) -> None:
        if self.state is not expected:
            raise InvalidTransition(
                f'expected {expected.value}, current state is {self.state.value}'
            )
