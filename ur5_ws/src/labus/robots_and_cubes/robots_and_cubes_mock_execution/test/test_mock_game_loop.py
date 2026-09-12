"""Complete hardware-free game-loop coverage through mock execution semantics."""

from robots_and_cubes_game.contracts import ExecutionResult
from robots_and_cubes_game.game_manager import GameManager
from robots_and_cubes_game.models import GameMode
from robots_and_cubes_game.state_machine import GameState

from robots_and_cubes_mock_execution.mock_engine import (
    MockExecutionEngine,
    MockOutcome,
    MockScenario,
    MockStage,
)


class MockGameLoop:
    """Connect the game manager to the same synthetic stage/result behavior."""

    def __init__(self, settings):
        self.engine = MockExecutionEngine(0.0)
        self.operations = []
        self.events = []
        self.manager = GameManager(
            settings,
            self.dispatch,
            'SYNTHETIC_MOCK_CONFIGURATION_ONLY',
            'SYNTHETIC_MOCK_CALIBRATION_ONLY',
            event_writer=lambda *event: self.events.append(event),
            preflight=lambda: (True, ''),
        )

    def dispatch(self, operation):
        self.operations.append(operation)
        terminal = self.engine.execute(
            lambda stage: self.manager.handle_execution_feedback(
                operation.operation_id, stage.name
            ),
            lambda _duration: True,
        )
        self.manager.handle_execution_result(ExecutionResult(
            operation.operation_id,
            terminal.outcome,
            terminal.error_code,
            terminal.error_summary,
            terminal.physical_progress,
        ))

    def ready_round(self, mode, seed=8):
        generated = self.manager.generate_round('generate', mode, seed)
        self.manager.confirm_physical_setup('setup', generated.snapshot.round_id)
        return self.manager.machine.round


def _cube(round_, correct):
    return next(
        cube.cube_id for cube in round_.cubes
        if round_.is_correct(cube.cube_id) is correct
    )


def test_standard_green_runs_mock_action_and_commits_success_after_result(settings):
    loop = MockGameLoop(settings)
    round_ = loop.ready_round(GameMode.STANDARD)
    result = loop.manager.submit_selection('green', round_.round_id, _cube(round_, True))
    assert result.accepted and result.requires_motion
    assert len(loop.operations) == 1
    assert loop.manager.machine.state is GameState.SUCCESS
    assert any(event[0] == 'motion_stage' for event in loop.events)
    assert any(event[0] == 'success' for event in loop.events)


def test_easy_wrong_colour_dispatches_and_consumes_a_completed_attempt(settings):
    loop = MockGameLoop(settings)
    round_ = loop.ready_round(GameMode.EASY)
    loop.manager.submit_selection('red', round_.round_id, _cube(round_, False))
    assert len(loop.operations) == 1
    assert loop.manager.machine.attempts_remaining == settings.game.attempts - 1


def test_wrong_selection_commits_only_after_mock_success_and_retry_is_safe(settings):
    loop = MockGameLoop(settings)
    round_ = loop.ready_round(GameMode.STANDARD)
    loop.engine.configure_next(MockScenario(MockOutcome.FAILURE, MockStage.PLANNING))
    loop.manager.submit_selection('fail', round_.round_id, _cube(round_, False))
    assert loop.manager.machine.state is GameState.ROBOT_ERROR
    assert loop.manager.machine.attempts_remaining == settings.game.attempts
    operation = loop.operations[-1]
    loop.manager.retry_operation('retry', round_.round_id, operation.operation_id)
    assert loop.manager.machine.state is GameState.WAITING_FOR_CHILD
    assert loop.manager.machine.attempts_remaining == settings.game.attempts - 1


def test_grasp_ambiguity_requires_reconciliation_before_a_retry(settings):
    loop = MockGameLoop(settings)
    round_ = loop.ready_round(GameMode.STANDARD)
    loop.engine.configure_next(MockScenario(MockOutcome.FAILURE, MockStage.GRASPING))
    loop.manager.submit_selection('grasp-failure', round_.round_id, _cube(round_, False))
    operation = loop.operations[-1]
    assert loop.manager.machine.state is GameState.ROBOT_ERROR
    assert not loop.manager.retry_operation(
        'unsafe', round_.round_id, operation.operation_id
    ).accepted
    assert loop.manager.reconcile_retry_safe(
        'source', round_.round_id, operation.operation_id
    ).accepted
    assert loop.manager.retry_operation('safe', round_.round_id, operation.operation_id).accepted


def test_beginner_destination_remains_policy_driven_for_mock_execution(settings):
    loop = MockGameLoop(settings)
    round_ = loop.ready_round(GameMode.BEGINNER, 7)
    target = round_.target_cube_id
    loop.manager.submit_selection('beginner', round_.round_id, target)
    assert loop.operations[-1].destination_policy == 'BEGINNER_CORRECT'
    assert loop.operations[-1].destination_id == settings.teaching.beginner_correct_destination
