"""ROS action server for the synthetic ExecutePickPlace application contract."""

from pathlib import Path
from threading import Lock
import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from robots_and_cubes_config import load_user_settings
from robots_and_cubes_interfaces.action import ExecutePickPlace
from robots_and_cubes_interfaces.srv import ConfigureMockOutcome

from .mock_engine import (
    MockOutcome,
    MockScenario,
    MockStage,
    MockTerminalResult,
    progress_after,
)
from .readiness import SyntheticMockReadiness


class MockExecutePickPlaceServer(Node):
    """Execute synthetic operations without any hardware, driver, or planner client."""

    def __init__(self, settings, disabled_cells=()) -> None:
        """Create the action and developer-only one-shot outcome configuration service."""
        if settings.execution_mode != 'MOCK':
            raise ValueError('mock executor requires application.execution_mode: MOCK')
        super().__init__('robots_and_cubes_mock_execute_pick_place')
        self._readiness = SyntheticMockReadiness(settings, frozenset(disabled_cells))
        self._stage_duration = settings.mock.movement_duration_seconds / len(MockStage)
        self._lock = Lock()
        self._active_operation_id = None
        self._next_scenario = MockScenario()
        self._configured_request_ids = set()
        self._server = ActionServer(
            self,
            ExecutePickPlace,
            'execute_pick_place',
            execute_callback=self._execute,
            goal_callback=self._goal,
            cancel_callback=self._cancel,
        )
        self.create_service(
            ConfigureMockOutcome, 'configure_mock_outcome', self._configure_outcome
        )

    def destroy_node(self):
        """Destroy only the application action server and its local ROS resources."""
        self._server.destroy()
        return super().destroy_node()

    def _goal(self, goal) -> GoalResponse:
        """Reserve the single application operation slot before accepting a goal."""
        if not goal.operation_id:
            return GoalResponse.REJECT
        with self._lock:
            if self._active_operation_id is not None:
                return GoalResponse.REJECT
            self._active_operation_id = goal.operation_id
        return GoalResponse.ACCEPT

    @staticmethod
    def _cancel(_goal_handle) -> CancelResponse:
        """Accept cancellation; execution observes it between short waits."""
        return CancelResponse.ACCEPT

    def _configure_outcome(self, request, response):
        """Configure exactly one deterministic synthetic terminal behavior."""
        with self._lock:
            if not request.request_id or request.request_id in self._configured_request_ids:
                response.accepted = bool(request.request_id)
                response.summary = (
                    'duplicate mock outcome request'
                    if request.request_id else 'request id is required'
                )
                return response
            try:
                outcome = MockOutcome(request.outcome)
                stage = MockStage[request.failure_stage or 'PLANNING']
                progress = None
                if request.use_explicit_physical_progress:
                    progress = type(progress_after(stage))(request.physical_progress)
            except (KeyError, ValueError):
                response.accepted = False
                response.summary = 'invalid mock outcome, stage, or physical progress'
                return response
            self._configured_request_ids.add(request.request_id)
            self._next_scenario = MockScenario(outcome, stage, progress)
        response.accepted = True
        response.summary = 'next mock operation configured'
        return response

    def _execute(self, goal_handle):
        """Publish ordered feedback and terminate promptly on injected/client cancellation."""
        goal = goal_handle.request
        try:
            valid, summary = self._readiness.validate_goal(goal)
            if not valid:
                return self._finish(
                    goal_handle,
                    MockTerminalResult(2, 10, summary, 1),
                )
            with self._lock:
                scenario, self._next_scenario = self._next_scenario, MockScenario()
            for stage in MockStage:
                feedback = ExecutePickPlace.Feedback()
                feedback.stage = int(stage)
                feedback.detail = f'synthetic mock: {stage.name}'
                goal_handle.publish_feedback(feedback)
                if scenario.outcome is MockOutcome.FAILURE and stage is scenario.failure_stage:
                    return self._finish(goal_handle, MockTerminalResult(
                        2,
                        10 if stage is MockStage.PLANNING else (
                            12 if stage is MockStage.GRASPING else 11
                        ),
                        f'mock failure injected at {stage.name}',
                        scenario.physical_progress or progress_after(stage),
                    ))
                if scenario.outcome is MockOutcome.CANCELED and stage is scenario.failure_stage:
                    return self._finish(goal_handle, MockTerminalResult(
                        1, 13, f'mock cancellation injected at {stage.name}',
                        scenario.physical_progress or progress_after(stage),
                    ))
                if not self._wait_for_stage_or_cancel(goal_handle):
                    return self._finish(goal_handle, MockTerminalResult(
                        1, 13, 'mock operation canceled by client', progress_after(stage),
                    ))
            return self._finish(goal_handle, MockTerminalResult(0, 0, '', 0))
        finally:
            with self._lock:
                self._active_operation_id = None

    def _wait_for_stage_or_cancel(self, goal_handle) -> bool:
        """Wait in an action worker while checking cancellation at short intervals."""
        remaining = self._stage_duration
        while remaining > 0.0:
            if goal_handle.is_cancel_requested:
                return False
            interval = min(remaining, 0.02)
            time.sleep(interval)
            remaining -= interval
        return not goal_handle.is_cancel_requested

    @staticmethod
    def _finish(goal_handle, terminal) -> ExecutePickPlace.Result:
        """Map stable application semantics to the one public action result."""
        result = ExecutePickPlace.Result()
        result.outcome = int(terminal.outcome)
        result.error.code = int(terminal.error_code)
        result.error.summary = terminal.error_summary
        result.error.recoverable = terminal.outcome != 0
        result.error.physical_progress = int(terminal.physical_progress)
        result.physical_progress = int(terminal.physical_progress)
        if terminal.outcome == 0:
            goal_handle.succeed()
        elif terminal.outcome == 1:
            goal_handle.canceled()
        else:
            goal_handle.abort()
        return result


def _disabled_cells(value) -> tuple[tuple[int, int], ...]:
    """Parse optional test-only cell exclusions without treating them as commissioning."""
    if not value or value == '[]':
        return ()
    values = [value] if isinstance(value, str) else value
    return tuple(tuple(int(part) for part in item.split(',', 1)) for item in values)


def _settings_from_ros_parameters() -> tuple[object, tuple[tuple[int, int], ...]]:
    """Read only normal mock configuration; no runtime hardware files are loaded."""
    bootstrap = Node('robots_and_cubes_mock_configuration')
    try:
        path = bootstrap.declare_parameter('user_settings_path', '').value
        disabled = bootstrap.declare_parameter('disabled_cells', '').value
        mode = bootstrap.declare_parameter('execution_mode', 'MOCK').value
    finally:
        bootstrap.destroy_node()
    if not path:
        raise RuntimeError('user_settings_path is required for application mock mode')
    if mode != 'MOCK':
        raise RuntimeError(f'execution mode {mode!r} is unsupported; mock is MOCK only')
    settings = load_user_settings(Path(path))
    if settings.execution_mode != 'MOCK':
        raise RuntimeError('application.execution_mode must be MOCK for mock launch')
    return settings, _disabled_cells(disabled)


def main() -> None:
    """Run only the synthetic action server; it starts no hardware stack."""
    rclpy.init()
    try:
        settings, disabled_cells = _settings_from_ros_parameters()
        node = MockExecutePickPlaceServer(settings, disabled_cells)
        executor = MultiThreadedExecutor(num_threads=2)
        executor.add_node(node)
        try:
            executor.spin()
        finally:
            executor.shutdown()
            node.destroy_node()
    finally:
        rclpy.shutdown()
