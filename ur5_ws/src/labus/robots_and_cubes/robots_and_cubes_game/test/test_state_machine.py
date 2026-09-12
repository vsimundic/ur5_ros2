import pytest

from robots_and_cubes_game.models import GameMode
from robots_and_cubes_game.round_generator import RoundGenerator
from robots_and_cubes_game.state_machine import (
    GameState,
    GameStateMachine,
    InvalidTransition,
    PhysicalProgress,
    SelectionDisposition,
)


def _waiting_machine(settings, mode=GameMode.STANDARD, seed=1):
    machine = GameStateMachine()
    machine.ready()
    machine.set_round(RoundGenerator(settings).generate(mode, seed))
    machine.request_physical_setup()
    machine.confirm_physical_setup()
    machine.complete_preflight(True)
    assert machine.state is GameState.WAITING_FOR_CHILD
    return machine


def _cube_id(machine, correct):
    return next(
        cube.cube_id
        for cube in machine.round.cubes
        if machine.round.is_correct(cube.cube_id) is correct
    )


def test_full_setup_flow_and_correct_first_attempt(settings):
    machine = _waiting_machine(settings)
    correct = _cube_id(machine, True)
    assert machine.submit_selection(correct) is SelectionDisposition.EXECUTION_REQUIRED
    assert machine.state is GameState.EXECUTING_SELECTION
    machine.complete_motion(True)
    assert machine.state is GameState.SUCCESS
    assert machine.attempts_remaining == 2
    assert correct in machine.removed_cubes


def test_wrong_then_correct_consumes_only_completed_wrong_attempt(settings):
    machine = _waiting_machine(settings)
    wrong = _cube_id(machine, False)
    machine.submit_selection(wrong)
    machine.complete_motion(True)
    assert machine.state is GameState.WAITING_FOR_CHILD
    assert machine.attempts_remaining == 1
    assert wrong in machine.selected_answers

    machine.submit_selection(_cube_id(machine, True))
    machine.complete_motion(True)
    assert machine.state is GameState.SUCCESS
    assert machine.attempts_remaining == 1


def test_all_attempts_wrong_reaches_failed(settings):
    machine = _waiting_machine(settings)
    wrong_ids = [
        cube.cube_id
        for cube in machine.round.cubes
        if not machine.round.is_correct(cube.cube_id)
    ]
    for cube_id in wrong_ids[:2]:
        machine.submit_selection(cube_id)
        machine.complete_motion(True)
    assert machine.state is GameState.FAILED
    assert machine.attempts_remaining == 0


def test_robot_failure_preserves_attempt_and_supports_retry(settings):
    machine = _waiting_machine(settings)
    wrong = _cube_id(machine, False)
    machine.submit_selection(wrong)
    machine.complete_motion(False, 'PLANNING_FAILED')
    assert machine.state is GameState.ROBOT_ERROR
    assert machine.attempts_remaining == 2
    assert wrong not in machine.selected_answers
    assert machine.pending_cube_id == wrong
    assert machine.last_robot_error == 'PLANNING_FAILED'

    machine.retry_motion()
    machine.complete_motion(True)
    assert machine.state is GameState.WAITING_FOR_CHILD
    assert machine.attempts_remaining == 1


def test_partial_motion_failure_requires_reconciliation_before_retry(settings):
    machine = _waiting_machine(settings)
    machine.submit_selection(_cube_id(machine, False), 'operation-1')
    machine.complete_motion(
        False, 'EXECUTION_FAILED', PhysicalProgress.MAY_HAVE_GRASPED
    )
    with pytest.raises(InvalidTransition, match='reconciliation'):
        machine.retry_motion()
    machine.confirm_retry_safe_after_reconciliation()
    machine.retry_motion()
    assert machine.state is GameState.EXECUTING_SELECTION


def test_easy_wrong_selection_has_no_motion_or_attempt_cost(settings):
    machine = _waiting_machine(settings, GameMode.EASY)
    wrong = _cube_id(machine, False)
    assert machine.submit_selection(wrong) is SelectionDisposition.EASY_HINT
    assert machine.state is GameState.WAITING_FOR_CHILD
    assert machine.attempts_remaining == 2
    assert machine.pending_cube_id is None
    assert wrong not in machine.selected_answers


def test_beginner_correctness_uses_target_identity_not_color(settings):
    machine = _waiting_machine(settings, GameMode.BEGINNER, seed=7)
    target = machine.round.beginner_target_cube_id
    assert target is not None
    assert machine.round.is_correct(target)
    machine.submit_selection(target)
    machine.complete_motion(True)
    assert machine.state is GameState.SUCCESS


def test_failed_preflight_enters_robot_error_without_selection_retry(settings):
    machine = GameStateMachine()
    machine.ready()
    machine.set_round(RoundGenerator(settings).generate(GameMode.STANDARD, 9))
    machine.request_physical_setup()
    machine.confirm_physical_setup()
    machine.complete_preflight(False, 'CELL_UNREACHABLE')
    assert machine.state is GameState.ROBOT_ERROR
    assert machine.attempts_remaining == 2
    with pytest.raises(InvalidTransition, match='no failed selection'):
        machine.retry_motion()


def test_completed_answer_cannot_be_selected_again(settings):
    machine = _waiting_machine(settings)
    wrong = _cube_id(machine, False)
    machine.submit_selection(wrong)
    machine.complete_motion(True)
    with pytest.raises(ValueError, match='no longer selectable'):
        machine.submit_selection(wrong)


@pytest.mark.parametrize(
    'state',
    [
        GameState.ROUND_GENERATED,
        GameState.WAITING_FOR_PHYSICAL_SETUP,
        GameState.ROUND_PREFLIGHT,
        GameState.WAITING_FOR_CHILD,
        GameState.EXECUTING_SELECTION,
        GameState.SUCCESS,
        GameState.FAILED,
        GameState.ROBOT_ERROR,
        GameState.CALIBRATION,
        GameState.TEACHING_POSITION,
    ],
)
def test_abort_from_meaningful_states_returns_clean_idle(settings, state):
    machine = GameStateMachine()
    machine.ready()
    machine.set_round(RoundGenerator(settings).generate(GameMode.STANDARD, 3))
    machine.state = state
    machine.begin_abort()
    assert machine.state is GameState.ABORTING
    machine.finish_abort()
    assert machine.state is GameState.IDLE
    assert machine.round is None
    assert machine.attempts_remaining == 0


def test_invalid_transition_is_rejected():
    machine = GameStateMachine()
    with pytest.raises(InvalidTransition):
        machine.set_round(None)


@pytest.mark.parametrize(
    ('start_method', 'expected_state'),
    [
        ('start_calibration', GameState.CALIBRATION),
        ('start_teaching_position', GameState.TEACHING_POSITION),
    ],
)
def test_operator_workflows_return_to_idle(start_method, expected_state):
    machine = GameStateMachine()
    machine.ready()
    getattr(machine, start_method)()
    assert machine.state is expected_state
    machine.finish_operator_workflow()
    assert machine.state is GameState.IDLE
