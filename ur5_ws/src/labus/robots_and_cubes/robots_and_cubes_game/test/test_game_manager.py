"""Hardware-free coverage for the serialized application boundary."""

from robots_and_cubes_game.contracts import (
    ExecutionErrorCode,
    ExecutionOutcome,
    ExecutionResult,
)
from robots_and_cubes_game.game_manager import GameManager
from robots_and_cubes_game.models import GameMode
from robots_and_cubes_game.state_machine import GameState, PhysicalProgress


class Recorder:
    """Record application action dispatches without implementing an executor."""

    def __init__(self):
        self.operations = []

    def __call__(self, operation):
        self.operations.append(operation)


def _manager(settings):
    recorder = Recorder()
    manager = GameManager(settings, recorder, 'config-a', 'calibration-a')
    return manager, recorder


def _waiting_manager(settings, mode=GameMode.STANDARD, seed=8):
    manager, recorder = _manager(settings)
    generated = manager.generate_round('generate-1', mode, seed)
    assert generated.accepted
    setup = manager.confirm_physical_setup('setup-1', generated.snapshot.round_id)
    assert setup.accepted
    manager.complete_preflight(True)
    return manager, recorder


def _cube_id(manager, correct):
    return next(
        cube.cube_id for cube in manager.machine.round.cubes
        if manager.machine.round.is_correct(cube.cube_id) is correct
    )


def _succeed(manager, recorder):
    operation = recorder.operations[-1]
    assert manager.handle_execution_result(ExecutionResult(
        operation.operation_id, ExecutionOutcome.SUCCEEDED,
    ))


def test_correct_first_attempt_dispatches_once_and_completes(settings):
    manager, recorder = _waiting_manager(settings)
    result = manager.submit_selection(
        'select-1', manager.machine.round.round_id, _cube_id(manager, True)
    )
    assert result.accepted and result.requires_motion
    assert manager.machine.state is GameState.EXECUTING_SELECTION
    _succeed(manager, recorder)
    assert manager.machine.state is GameState.SUCCESS
    assert manager.snapshot().state_version == 6


def test_wrong_then_correct_commits_attempt_only_after_success(settings):
    manager, recorder = _waiting_manager(settings)
    manager.submit_selection('wrong-1', manager.machine.round.round_id, _cube_id(manager, False))
    _succeed(manager, recorder)
    assert manager.machine.attempts_remaining == 1
    manager.submit_selection('right-1', manager.machine.round.round_id, _cube_id(manager, True))
    _succeed(manager, recorder)
    assert manager.machine.state is GameState.SUCCESS


def test_all_attempts_wrong_reaches_failed(settings):
    manager, recorder = _waiting_manager(settings)
    wrong = [cube.cube_id for cube in manager.machine.round.cubes if cube.kind.value == 'red']
    for index, cube_id in enumerate(wrong[:manager.machine.attempts_remaining]):
        manager.submit_selection(f'wrong-{index}', manager.machine.round.round_id, cube_id)
        _succeed(manager, recorder)
    assert manager.machine.state is GameState.FAILED


def test_easy_red_tap_has_no_operation_or_attempt_cost(settings):
    manager, recorder = _waiting_manager(settings, GameMode.EASY)
    result = manager.submit_selection(
        'red-tap', manager.machine.round.round_id, _cube_id(manager, False)
    )
    assert result.accepted and not result.requires_motion
    assert not recorder.operations
    assert manager.machine.attempts_remaining == 2


def test_beginner_uses_location_target_not_green_color(settings):
    manager, recorder = _waiting_manager(settings, GameMode.BEGINNER, 7)
    target = manager.machine.round.beginner_target_cube_id
    assert target is not None
    assert manager.snapshot().beginner_target_coordinate == (
        manager.machine.round.cube(target).game_coordinate
    )
    manager.submit_selection('target', manager.machine.round.round_id, target)
    _succeed(manager, recorder)
    assert manager.machine.state is GameState.SUCCESS


def test_motion_failure_and_cancellation_preserve_attempts(settings):
    manager, recorder = _waiting_manager(settings)
    manager.submit_selection('fail', manager.machine.round.round_id, _cube_id(manager, False))
    operation = recorder.operations[-1]
    manager.handle_execution_result(ExecutionResult(
        operation.operation_id, ExecutionOutcome.FAILED,
        ExecutionErrorCode.PLANNING_FAILED,
    ))
    assert manager.machine.attempts_remaining == 2
    retry = manager.retry_operation(
        'retry', manager.machine.round.round_id, operation.operation_id
    )
    assert retry.accepted
    operation = recorder.operations[-1]
    manager.handle_execution_result(ExecutionResult(
        operation.operation_id, ExecutionOutcome.CANCELED,
        ExecutionErrorCode.CANCELED,
    ))
    assert manager.machine.attempts_remaining == 2
    assert manager.machine.state is GameState.ROBOT_ERROR


def test_duplicate_stale_and_second_selection_are_safe(settings):
    manager, recorder = _waiting_manager(settings)
    cube_id = _cube_id(manager, True)
    first = manager.submit_selection('once', manager.machine.round.round_id, cube_id)
    duplicate = manager.submit_selection('once', manager.machine.round.round_id, cube_id)
    second = manager.submit_selection('twice', manager.machine.round.round_id, cube_id)
    stale = manager.submit_selection('stale', 'old-round', cube_id)
    assert first.accepted and duplicate.accepted
    assert len(recorder.operations) == 1
    assert not second.accepted and second.error_code is ExecutionErrorCode.INVALID_STATE
    assert not stale.accepted


def test_latest_snapshot_listener_and_versions_reconnect(settings):
    manager, _ = _manager(settings)
    received = []
    manager.add_snapshot_listener(received.append)
    generated = manager.generate_round('generate', GameMode.STANDARD, 4)
    assert received[0].state_version == 0
    assert received[-1].state_version == generated.snapshot.state_version == 1
    assert manager.snapshot() == received[-1]


def test_partial_result_requires_reconciliation_before_retry(settings):
    manager, recorder = _waiting_manager(settings)
    manager.submit_selection('partial', manager.machine.round.round_id, _cube_id(manager, False))
    operation = recorder.operations[-1]
    manager.handle_execution_result(ExecutionResult(
        operation.operation_id, ExecutionOutcome.FAILED,
        ExecutionErrorCode.EXECUTION_FAILED, 'lost contact',
        PhysicalProgress.MAY_HAVE_GRASPED,
    ))
    rejected = manager.retry_operation(
        'unsafe-retry', manager.machine.round.round_id, operation.operation_id
    )
    assert not rejected.accepted
    assert rejected.error_code is ExecutionErrorCode.RECONCILIATION_REQUIRED
    reconciled = manager.reconcile_retry_safe(
        'reconciled', manager.machine.round.round_id, operation.operation_id
    )
    assert reconciled.accepted
    assert manager.retry_operation(
        'safe-retry', manager.machine.round.round_id, operation.operation_id
    ).accepted


def test_abort_returns_idle_and_preserves_no_hidden_operation(settings):
    manager, _ = _waiting_manager(settings)
    result = manager.abort_round('abort', manager.machine.round.round_id)
    assert result.accepted
    assert manager.machine.state is GameState.IDLE
    assert manager.snapshot().round_id is None
