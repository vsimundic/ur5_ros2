"""Serialized application boundary around the pure Robots and Cubes game core."""

from collections.abc import Callable
from typing import Optional
from uuid import uuid4

from robots_and_cubes_config.models import UserSettings

from .contracts import (
    ExecutionErrorCode,
    ExecutionOutcome,
    ExecutionResult,
    GameSnapshot,
    IntentResult,
    OperationRequest,
    SnapshotCube,
)
from .models import GameMode
from .round_generator import RoundGenerator
from .state_machine import (
    GameState,
    GameStateMachine,
    InvalidTransition,
    PhysicalProgress,
    SelectionDisposition,
)


OperationDispatcher = Callable[[OperationRequest], None]
SnapshotListener = Callable[[GameSnapshot], None]
EventWriter = Callable[[str, int, Optional[str], Optional[str], dict], None]


class GameManager:
    """Serialize external intents without giving ROS or motion code game authority."""

    def __init__(
        self,
        settings: UserSettings,
        dispatch_operation: OperationDispatcher,
        configuration_revision: str = 'unversioned',
        calibration_revision: str = '',
        event_writer: Optional[EventWriter] = None,
    ) -> None:
        """Create an idle manager; construction neither contacts nor commands hardware."""
        self._generator = RoundGenerator(settings)
        self._machine = GameStateMachine()
        self._machine.ready()
        self._dispatch_operation = dispatch_operation
        self._configuration_revision = configuration_revision
        self._calibration_revision = calibration_revision
        self._event_writer = event_writer
        self._state_version = 0
        self._pending_request_id: Optional[str] = None
        self._receipts: set[str] = set()
        self._listeners: list[SnapshotListener] = []

    @property
    def machine(self) -> GameStateMachine:
        """Expose the pure state machine for read-only inspection and tests."""
        return self._machine

    def add_snapshot_listener(self, listener: SnapshotListener) -> None:
        """Register a publisher or gateway observer for complete snapshots."""
        self._listeners.append(listener)
        listener(self.snapshot())

    def snapshot(self) -> GameSnapshot:
        """Return a complete, self-contained current state snapshot."""
        game_round = self._machine.round
        cubes = () if game_round is None else tuple(
            SnapshotCube(
                cube_id=cube.cube_id,
                kind=cube.kind,
                cell=cube.cell,
                game_coordinate=cube.game_coordinate,
                removed=cube.cube_id in self._machine.removed_cubes,
            )
            for cube in game_round.cubes
        )
        error_code = self._error_code(self._machine.last_robot_error)
        progress = self._machine.physical_progress
        beginner_target = (
            None if game_round is None or game_round.beginner_target_cube_id is None
            else game_round.cube(game_round.beginner_target_cube_id).game_coordinate
        )
        operation_state = (
            'reconciliation_required'
            if self._machine.state is GameState.ROBOT_ERROR
            and progress >= PhysicalProgress.MAY_HAVE_GRASPED
            else 'executing'
            if self._machine.state is GameState.EXECUTING_SELECTION
            else 'idle'
        )
        return GameSnapshot(
            schema_version=1,
            state_version=self._state_version,
            round_id=None if game_round is None else game_round.round_id,
            mode=None if game_round is None else game_round.mode.value,
            game_state=self._machine.state.value,
            origin_cell=None if game_round is None else game_round.origin_cell,
            rotation_deg=None if game_round is None else int(game_round.rotation),
            handedness=None if game_round is None else game_round.handedness.value,
            beginner_target_coordinate=beginner_target,
            cubes=cubes,
            answer_order=() if game_round is None else game_round.answer_order,
            selected_answer_ids=tuple(sorted(self._machine.selected_answers)),
            disabled_answer_ids=tuple(sorted(self._machine.removed_cubes)),
            attempts_remaining=self._machine.attempts_remaining,
            operation_state=operation_state,
            pending_request_id=self._pending_request_id,
            pending_operation_id=self._machine.pending_operation_id,
            game_flow_ready=self._machine.state is GameState.WAITING_FOR_CHILD,
            error_code=error_code,
            error_summary=self._machine.last_robot_error or '',
            error_recoverable=self._machine.state is GameState.ROBOT_ERROR,
            physical_progress=progress,
        )

    def generate_round(
        self, request_id: str, mode: GameMode, seed: int | None = None
    ) -> IntentResult:
        """Generate one immutable round once for a unique request identifier."""
        duplicate = self._duplicate(request_id)
        if duplicate is not None:
            return duplicate
        if self._machine.state is not GameState.IDLE:
            return self._reject(request_id, ExecutionErrorCode.INVALID_STATE, 'not idle')
        try:
            game_round = self._generator.generate(mode, seed)
            self._machine.set_round(game_round)
            self._advance('round_generated', request_id, {'seed': game_round.random_seed})
            return self._accept(False)
        except (TypeError, ValueError, RuntimeError) as error:
            return self._reject(request_id, ExecutionErrorCode.INVALID_STATE, str(error))

    def request_physical_setup(self, request_id: str, round_id: str) -> IntentResult:
        """Enter the operator setup state for the requested current round."""
        return self._round_transition(
            request_id, round_id, self._machine.request_physical_setup,
            'physical_setup_requested',
        )

    def confirm_physical_setup(self, request_id: str, round_id: str) -> IntentResult:
        """Record setup confirmation; later motion integration supplies preflight."""
        if self._machine.state is GameState.ROUND_GENERATED:
            setup = self.request_physical_setup(f'{request_id}:setup', round_id)
            if not setup.accepted:
                return setup
        return self._round_transition(
            request_id, round_id, self._machine.confirm_physical_setup,
            'physical_setup_confirmed',
        )

    def complete_preflight(self, valid: bool, error: str = 'PREFLIGHT_FAILED') -> None:
        """Accept a future internal preflight result; no hardware action occurs here."""
        self._machine.complete_preflight(valid, error)
        self._advance('preflight_completed', None, {'valid': valid, 'error': error})

    def submit_selection(
        self, request_id: str, round_id: str, cube_id: str
    ) -> IntentResult:
        """Accept one child selection and dispatch at most one physical operation."""
        duplicate = self._duplicate(request_id)
        if duplicate is not None:
            return duplicate
        stale = self._check_round(request_id, round_id)
        if stale is not None:
            return stale
        if self._machine.state is not GameState.WAITING_FOR_CHILD:
            return self._reject(
                request_id, ExecutionErrorCode.INVALID_STATE, 'selection is locked'
            )
        operation_id = str(uuid4())
        try:
            disposition = self._machine.submit_selection(cube_id, operation_id)
        except (KeyError, ValueError, InvalidTransition) as error:
            return self._reject(request_id, ExecutionErrorCode.INVALID_SELECTION, str(error))
        if disposition is SelectionDisposition.EASY_HINT:
            self._advance('selection_received', request_id, {'cube_id': cube_id, 'motion': False})
            return self._accept(False)
        self._pending_request_id = request_id
        game_round = self._machine.round
        assert game_round is not None
        cube = game_round.cube(cube_id)
        destination_id = 'green_reward' if game_round.is_correct(cube_id) else 'red_drop'
        operation = OperationRequest(
            request_id=request_id,
            operation_id=operation_id,
            round_id=game_round.round_id,
            cube_id=cube_id,
            cell=cube.cell,
            destination_id=destination_id,
            destination_policy='configured_destination',
            configuration_revision=self._configuration_revision,
            calibration_revision=self._calibration_revision,
        )
        self._advance('motion_requested', request_id, {'operation_id': operation_id})
        try:
            self._dispatch_operation(operation)
        except Exception as error:  # Dispatcher failures must become recoverable game errors.
            self.handle_execution_result(ExecutionResult(
                operation_id=operation_id,
                outcome=ExecutionOutcome.FAILED,
                error_code=ExecutionErrorCode.UNKNOWN,
                error_summary=str(error),
            ))
        return self._accept(True)

    def handle_execution_result(self, result: ExecutionResult) -> bool:
        """Commit only successful physical operations; preserve failures for recovery."""
        if result.operation_id != self._machine.pending_operation_id:
            return False
        succeeded = result.outcome is ExecutionOutcome.SUCCEEDED
        error = result.error_code.name if result.error_code is not ExecutionErrorCode.NONE else ''
        self._machine.complete_motion(succeeded, error, result.physical_progress)
        if succeeded:
            self._pending_request_id = None
            event = 'motion_completed'
            if self._machine.state is GameState.SUCCESS:
                event = 'success'
            elif self._machine.state is GameState.FAILED:
                event = 'round_failed'
            elif self._machine.state is GameState.WAITING_FOR_CHILD:
                event = 'wrong_answer_committed'
        else:
            event = 'robot_error'
        self._advance(event, None, {
            'operation_id': result.operation_id,
            'outcome': result.outcome.name,
        })
        return True

    def retry_operation(
        self, request_id: str, round_id: str, operation_id: str
    ) -> IntentResult:
        """Re-dispatch only a failed operation known to have no partial effect."""
        duplicate = self._duplicate(request_id)
        if duplicate is not None:
            return duplicate
        stale = self._check_round(request_id, round_id)
        if stale is not None:
            return stale
        if operation_id != self._machine.pending_operation_id:
            return self._reject(
                request_id, ExecutionErrorCode.INVALID_STATE, 'operation is not pending'
            )
        try:
            self._machine.retry_motion()
        except InvalidTransition as error:
            return self._reject(request_id, ExecutionErrorCode.RECONCILIATION_REQUIRED, str(error))
        self._pending_request_id = request_id
        operation = self._operation_for_pending(request_id)
        self._advance('retry_recovery', request_id, {'operation_id': operation.operation_id})
        try:
            self._dispatch_operation(operation)
        except Exception as error:
            self.handle_execution_result(ExecutionResult(
                operation_id=operation.operation_id,
                outcome=ExecutionOutcome.FAILED,
                error_code=ExecutionErrorCode.UNKNOWN,
                error_summary=str(error),
            ))
        return self._accept(True)

    def reconcile_retry_safe(
        self, request_id: str, round_id: str, operation_id: str
    ) -> IntentResult:
        """Record operator confirmation before an ambiguous operation may be retried."""
        duplicate = self._duplicate(request_id)
        if duplicate is not None:
            return duplicate
        stale = self._check_round(request_id, round_id)
        if stale is not None:
            return stale
        if operation_id != self._machine.pending_operation_id:
            return self._reject(
                request_id, ExecutionErrorCode.INVALID_STATE, 'operation is not pending'
            )
        try:
            self._machine.confirm_retry_safe_after_reconciliation()
        except InvalidTransition as error:
            return self._reject(request_id, ExecutionErrorCode.RECONCILIATION_REQUIRED, str(error))
        self._advance('operator_reconciliation', request_id, {'operation_id': operation_id})
        return self._accept(False)

    def abort_round(self, request_id: str, round_id: str) -> IntentResult:
        """Abort an active round without treating this as a robot-home command."""
        duplicate = self._duplicate(request_id)
        if duplicate is not None:
            return duplicate
        stale = self._check_round(request_id, round_id)
        if stale is not None:
            return stale
        try:
            self._machine.begin_abort()
            self._machine.finish_abort()
        except InvalidTransition as error:
            return self._reject(request_id, ExecutionErrorCode.INVALID_STATE, str(error))
        self._pending_request_id = None
        self._advance('operator_abort', request_id, {})
        return self._accept(False)

    def _operation_for_pending(self, request_id: str) -> OperationRequest:
        game_round = self._machine.round
        cube_id = self._machine.pending_cube_id
        operation_id = self._machine.pending_operation_id
        assert game_round is not None and cube_id is not None and operation_id is not None
        cube = game_round.cube(cube_id)
        destination_id = 'green_reward' if game_round.is_correct(cube_id) else 'red_drop'
        return OperationRequest(
            request_id=request_id,
            operation_id=operation_id,
            round_id=game_round.round_id,
            cube_id=cube_id,
            cell=cube.cell,
            destination_id=destination_id,
            destination_policy='configured_destination',
            configuration_revision=self._configuration_revision,
            calibration_revision=self._calibration_revision,
        )

    def _round_transition(
        self,
        request_id: str,
        round_id: str,
        transition: Callable[[], None],
        event: str,
    ) -> IntentResult:
        duplicate = self._duplicate(request_id)
        if duplicate is not None:
            return duplicate
        stale = self._check_round(request_id, round_id)
        if stale is not None:
            return stale
        try:
            transition()
        except InvalidTransition as error:
            return self._reject(request_id, ExecutionErrorCode.INVALID_STATE, str(error))
        self._advance(event, request_id, {})
        return self._accept(False)

    def _check_round(self, request_id: str, round_id: str) -> IntentResult | None:
        game_round = self._machine.round
        if game_round is None or round_id != game_round.round_id:
            return self._reject(
                request_id, ExecutionErrorCode.STALE_ROUND, 'stale round id'
            )
        return None

    def _duplicate(self, request_id: str) -> IntentResult | None:
        if not request_id:
            return self._reject(
                request_id, ExecutionErrorCode.INVALID_STATE, 'request id is required'
            )
        if request_id in self._receipts:
            return IntentResult(True, False, ExecutionErrorCode.NONE, '', self.snapshot())
        self._receipts.add(request_id)
        return None

    def _accept(self, requires_motion: bool) -> IntentResult:
        return IntentResult(True, requires_motion, ExecutionErrorCode.NONE, '', self.snapshot())

    def _reject(
        self, request_id: str, code: ExecutionErrorCode, summary: str
    ) -> IntentResult:
        if request_id:
            self._receipts.add(request_id)
        return IntentResult(False, False, code, summary, self.snapshot())

    def _advance(self, event: str, request_id: Optional[str], payload: dict) -> None:
        self._state_version += 1
        snapshot = self.snapshot()
        if self._event_writer is not None:
            self._event_writer(
                event, snapshot.state_version, snapshot.round_id, request_id, payload
            )
        for listener in self._listeners:
            listener(snapshot)

    @staticmethod
    def _error_code(error: Optional[str]) -> ExecutionErrorCode:
        if error is None:
            return ExecutionErrorCode.NONE
        return ExecutionErrorCode.__members__.get(error, ExecutionErrorCode.UNKNOWN)
