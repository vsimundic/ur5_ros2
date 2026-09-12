"""Deterministic, ROS-independent execution semantics for the application mock."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Callable

from robots_and_cubes_game.contracts import ExecutionErrorCode, ExecutionOutcome
from robots_and_cubes_game.state_machine import PhysicalProgress


class MockStage(IntEnum):
    """Stages shared exactly with the ExecutePickPlace application action."""

    PLANNING = 0
    MOVING_TO_PREGRASP = 1
    DESCENDING = 2
    GRASPING = 3
    LIFTING = 4
    MOVING_TO_DESTINATION = 5
    RELEASING = 6
    RETREATING = 7


class MockOutcome(IntEnum):
    """The deliberately configured terminal behavior of the next operation."""

    SUCCESS = 0
    FAILURE = 1
    CANCELED = 2


@dataclass(frozen=True)
class MockScenario:
    """One-shot deterministic failure injection, never random behavior."""

    outcome: MockOutcome = MockOutcome.SUCCESS
    failure_stage: MockStage = MockStage.PLANNING
    physical_progress: PhysicalProgress | None = None


@dataclass(frozen=True)
class MockTerminalResult:
    """A mapped action result without any robot or ROS dependency."""

    outcome: ExecutionOutcome
    error_code: ExecutionErrorCode
    error_summary: str
    physical_progress: PhysicalProgress


def progress_after(stage: MockStage) -> PhysicalProgress:
    """Return the conservative physical-progress classification for a stage."""
    if stage <= MockStage.DESCENDING:
        return PhysicalProgress.PLANNING
    if stage <= MockStage.LIFTING:
        return PhysicalProgress.MAY_HAVE_GRASPED
    if stage <= MockStage.MOVING_TO_DESTINATION:
        return PhysicalProgress.MAY_HAVE_TRANSPORTED
    return PhysicalProgress.MAY_HAVE_RELEASED


class MockExecutionEngine:
    """Run synthetic stages with prompt cooperative cancellation checks."""

    stages = tuple(MockStage)

    def __init__(self, stage_duration_seconds: float) -> None:
        """Create an engine with one configurable duration shared across stages."""
        if stage_duration_seconds < 0.0:
            raise ValueError('stage duration cannot be negative')
        self._stage_duration_seconds = stage_duration_seconds
        self._next_scenario = MockScenario()

    def configure_next(self, scenario: MockScenario) -> None:
        """Set the next operation outcome, consuming it exactly once."""
        self._next_scenario = scenario

    def execute(
        self,
        feedback: Callable[[MockStage], None],
        wait: Callable[[float], bool],
    ) -> MockTerminalResult:
        """Execute one operation; ``wait`` returns false when cancellation is requested."""
        scenario, self._next_scenario = self._next_scenario, MockScenario()
        last_stage = MockStage.PLANNING
        for stage in self.stages:
            last_stage = stage
            feedback(stage)
            if scenario.outcome is MockOutcome.FAILURE and stage is scenario.failure_stage:
                return self._failure(scenario, stage)
            if scenario.outcome is MockOutcome.CANCELED and stage is scenario.failure_stage:
                return self._canceled(scenario, stage)
            if not wait(self._stage_duration_seconds):
                return MockTerminalResult(
                    ExecutionOutcome.CANCELED,
                    ExecutionErrorCode.CANCELED,
                    'mock operation canceled by client',
                    progress_after(last_stage),
                )
        return MockTerminalResult(
            ExecutionOutcome.SUCCEEDED,
            ExecutionErrorCode.NONE,
            '',
            PhysicalProgress.NOT_STARTED,
        )

    @staticmethod
    def _failure(scenario: MockScenario, stage: MockStage) -> MockTerminalResult:
        code = (
            ExecutionErrorCode.PLANNING_FAILED if stage is MockStage.PLANNING
            else ExecutionErrorCode.GRIPPER_FAILED if stage is MockStage.GRASPING
            else ExecutionErrorCode.EXECUTION_FAILED
        )
        return MockTerminalResult(
            ExecutionOutcome.FAILED,
            code,
            f'mock failure injected at {stage.name}',
            scenario.physical_progress or progress_after(stage),
        )

    @staticmethod
    def _canceled(scenario: MockScenario, stage: MockStage) -> MockTerminalResult:
        return MockTerminalResult(
            ExecutionOutcome.CANCELED,
            ExecutionErrorCode.CANCELED,
            f'mock cancellation injected at {stage.name}',
            scenario.physical_progress or progress_after(stage),
        )
