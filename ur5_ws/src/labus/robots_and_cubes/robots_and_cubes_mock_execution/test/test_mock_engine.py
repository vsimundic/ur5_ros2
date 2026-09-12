"""Hardware-free behavior tests for the synthetic application executor."""

import pytest

from robots_and_cubes_game.contracts import ExecutionErrorCode, ExecutionOutcome
from robots_and_cubes_game.state_machine import PhysicalProgress

from robots_and_cubes_mock_execution.mock_engine import (
    MockExecutionEngine,
    MockOutcome,
    MockScenario,
    MockStage,
)


def _run(engine):
    stages = []
    return stages, engine.execute(stages.append, lambda _duration: True)


def test_success_emits_the_complete_ordered_application_stage_sequence():
    stages, result = _run(MockExecutionEngine(0.0))
    assert stages == list(MockStage)
    assert result.outcome is ExecutionOutcome.SUCCEEDED
    assert result.physical_progress is PhysicalProgress.NOT_STARTED


@pytest.mark.parametrize(
    ('stage', 'code', 'progress'),
    [
        (MockStage.PLANNING, ExecutionErrorCode.PLANNING_FAILED, PhysicalProgress.PLANNING),
        (MockStage.GRASPING, ExecutionErrorCode.GRIPPER_FAILED, PhysicalProgress.MAY_HAVE_GRASPED),
        (MockStage.MOVING_TO_DESTINATION, ExecutionErrorCode.EXECUTION_FAILED,
         PhysicalProgress.MAY_HAVE_TRANSPORTED),
        (MockStage.RELEASING, ExecutionErrorCode.EXECUTION_FAILED,
         PhysicalProgress.MAY_HAVE_RELEASED),
    ],
)
def test_deterministic_failure_injection_maps_stage_to_contract_semantics(
    stage, code, progress
):
    engine = MockExecutionEngine(0.0)
    engine.configure_next(MockScenario(MockOutcome.FAILURE, stage))
    stages, result = _run(engine)
    assert stages[-1] is stage
    assert result.outcome is ExecutionOutcome.FAILED
    assert result.error_code is code
    assert result.physical_progress is progress


@pytest.mark.parametrize('stage', (MockStage.PLANNING, MockStage.RELEASING))
def test_injected_cancellation_stops_without_subsequent_stages(stage):
    engine = MockExecutionEngine(0.0)
    engine.configure_next(MockScenario(MockOutcome.CANCELED, stage))
    stages, result = _run(engine)
    assert stages[-1] is stage
    assert result.outcome is ExecutionOutcome.CANCELED
    assert result.error_code is ExecutionErrorCode.CANCELED


def test_client_cancellation_is_checked_during_synthetic_progression():
    engine = MockExecutionEngine(0.0)
    stages = []
    result = engine.execute(stages.append, lambda _duration: False)
    assert stages == [MockStage.PLANNING]
    assert result.outcome is ExecutionOutcome.CANCELED
    assert result.physical_progress is PhysicalProgress.PLANNING


def test_next_injected_outcome_is_consumed_once():
    engine = MockExecutionEngine(0.0)
    engine.configure_next(MockScenario(MockOutcome.FAILURE, MockStage.PLANNING))
    assert _run(engine)[1].outcome is ExecutionOutcome.FAILED
    assert _run(engine)[1].outcome is ExecutionOutcome.SUCCEEDED
