"""ROS 2 adapter that publishes snapshots and dispatches application operations."""

from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

from robots_and_cubes_config.models import UserSettings

from robots_and_cubes_interfaces.action import ExecutePickPlace
from robots_and_cubes_interfaces.msg import CubeState, ErrorSummary, GameStateSnapshot
from robots_and_cubes_interfaces.srv import (
    AbortRound,
    ConfirmPhysicalSetup,
    GenerateRound,
    GetGameState,
    ReconcileOperation,
    RetryOperation,
    SubmitChildSelection,
)

from .contracts import ExecutionErrorCode, ExecutionOutcome, ExecutionResult, GameSnapshot
from .game_manager import GameManager
from .models import GameMode
from .state_machine import PhysicalProgress


class RosGameManagerNode(Node):
    """Thin ROS transport layer; game decisions remain in :class:`GameManager`."""

    def __init__(
        self,
        settings: UserSettings,
        configuration_revision: str = 'unversioned',
        calibration_revision: str = '',
        preflight=None,
        event_writer=None,
    ) -> None:
        """Create application services and a transient latest-snapshot publisher."""
        super().__init__('robots_and_cubes_game_manager')
        self._manager = GameManager(
            settings,
            self._dispatch_operation,
            configuration_revision,
            calibration_revision,
            event_writer=event_writer,
            preflight=preflight,
        )
        qos = QoSProfile(
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE,
        )
        self._snapshot_publisher = self.create_publisher(GameStateSnapshot, 'game_state', qos)
        self._motion_client = ActionClient(self, ExecutePickPlace, 'execute_pick_place')
        self.create_service(GenerateRound, 'generate_round', self._generate_round)
        self.create_service(ConfirmPhysicalSetup, 'confirm_physical_setup', self._confirm_setup)
        self.create_service(SubmitChildSelection, 'submit_child_selection', self._submit_selection)
        self.create_service(RetryOperation, 'retry_operation', self._retry_operation)
        self.create_service(ReconcileOperation, 'reconcile_operation', self._reconcile)
        self.create_service(AbortRound, 'abort_round', self._abort_round)
        self.create_service(GetGameState, 'get_game_state', self._get_game_state)
        self._manager.add_snapshot_listener(self._publish_snapshot)

    def _generate_round(self, request, response):
        modes = (
            GameMode.EASY, GameMode.BEGINNER, GameMode.STANDARD,
            GameMode.CHALLENGE, GameMode.SPATIAL,
        )
        if request.mode >= len(modes):
            response.accepted = False
            response.error = self._error_message(
                ExecutionErrorCode.INVALID_SELECTION,
                'unsupported game mode',
                self._manager.snapshot(),
            )
            response.snapshot = self._to_message(self._manager.snapshot())
            return response
        seed = request.seed if request.use_explicit_seed else None
        return self._fill_response(
            response, self._manager.generate_round(request.request_id, modes[request.mode], seed)
        )

    def _confirm_setup(self, request, response):
        return self._fill_response(
            response,
            self._manager.confirm_physical_setup(request.request_id, request.round_id),
        )

    def _submit_selection(self, request, response):
        return self._fill_response(
            response,
            self._manager.submit_selection(request.request_id, request.round_id, request.cube_id),
        )

    def _retry_operation(self, request, response):
        return self._fill_response(
            response,
            self._manager.retry_operation(
                request.request_id, request.round_id, request.operation_id
            ),
        )

    def _reconcile(self, request, response):
        if request.resolution != ReconcileOperation.Request.RETRY_SAFE:
            if request.resolution in (
                ReconcileOperation.Request.CUBE_HELD_OR_TRANSPORTED,
                ReconcileOperation.Request.CUBE_AT_DESTINATION,
            ):
                return self._fill_response(
                    response,
                    self._manager.reconcile_non_retryable(
                        request.request_id,
                        request.round_id,
                        request.operation_id,
                        'held_or_transported'
                        if request.resolution
                        == ReconcileOperation.Request.CUBE_HELD_OR_TRANSPORTED
                        else 'at_destination',
                    ),
                )
            return self._fill_response(
                response,
                self._manager.abort_round(request.request_id, request.round_id),
            )
        return self._fill_response(
            response,
            self._manager.reconcile_retry_safe(
                request.request_id, request.round_id, request.operation_id
            ),
        )

    def _abort_round(self, request, response):
        return self._fill_response(
            response, self._manager.abort_round(request.request_id, request.round_id)
        )

    def _get_game_state(self, request, response):
        del request
        response.snapshot = self._to_message(self._manager.snapshot())
        return response

    def _fill_response(self, response, result):
        response.accepted = result.accepted
        if hasattr(response, 'requires_motion'):
            response.requires_motion = result.requires_motion
        response.error = self._error_message(
            result.error_code, result.error_summary, result.snapshot
        )
        response.snapshot = self._to_message(result.snapshot)
        return response

    def _dispatch_operation(self, operation) -> None:
        """Send only an application action goal; no driver or MoveIt API is used here."""
        goal = ExecutePickPlace.Goal()
        goal.request_id = operation.request_id
        goal.operation_id = operation.operation_id
        goal.round_id = operation.round_id
        goal.cube_id = operation.cube_id
        goal.grid_column = operation.cell.column
        goal.grid_row = operation.cell.row
        goal.destination_id = operation.destination_id
        goal.destination_policy = operation.destination_policy
        goal.configuration_revision = operation.configuration_revision
        goal.calibration_revision = operation.calibration_revision
        future = self._motion_client.send_goal_async(
            goal,
            feedback_callback=lambda feedback: self._on_feedback(
                feedback, operation.operation_id
            ),
        )
        future.add_done_callback(
            lambda future: self._on_goal_response(future, operation.operation_id)
        )

    def _on_goal_response(self, future, operation_id: str) -> None:
        try:
            goal_handle = future.result()
            if not goal_handle.accepted:
                self._manager.handle_execution_result(ExecutionResult(
                    operation_id, ExecutionOutcome.FAILED, ExecutionErrorCode.UNKNOWN,
                    'operation goal rejected', PhysicalProgress.NOT_STARTED,
                ))
                return
            result_future = goal_handle.get_result_async()
            result_future.add_done_callback(
                lambda result_future: self._on_result(result_future, operation_id)
            )
        except Exception as error:
            self._manager.handle_execution_result(ExecutionResult(
                operation_id, ExecutionOutcome.FAILED, ExecutionErrorCode.UNKNOWN,
                str(error), PhysicalProgress.NOT_STARTED,
            ))

    def _on_result(self, future, operation_id: str) -> None:
        try:
            result = future.result().result
            outcome = ExecutionOutcome(result.outcome)
            error = ExecutionErrorCode(result.error.code)
            progress = PhysicalProgress(result.physical_progress)
            self._manager.handle_execution_result(ExecutionResult(
                operation_id, outcome, error, result.error.summary, progress
            ))
        except Exception as error:
            self._manager.handle_execution_result(ExecutionResult(
                operation_id, ExecutionOutcome.FAILED, ExecutionErrorCode.UNKNOWN,
                str(error), PhysicalProgress.NOT_STARTED,
            ))

    def _on_feedback(self, feedback_message, operation_id: str) -> None:
        """Expose stable application stages without controller/planner detail."""
        names = (
            'PLANNING', 'MOVING_TO_PREGRASP', 'DESCENDING', 'GRASPING',
            'LIFTING', 'MOVING_TO_DESTINATION', 'RELEASING', 'RETREATING',
        )
        stage = feedback_message.feedback.stage
        if 0 <= stage < len(names):
            self._manager.handle_execution_feedback(operation_id, names[stage])

    def _publish_snapshot(self, snapshot: GameSnapshot) -> None:
        self._snapshot_publisher.publish(self._to_message(snapshot))

    def _to_message(self, snapshot: GameSnapshot) -> GameStateSnapshot:
        message = GameStateSnapshot()
        message.schema_version = snapshot.schema_version
        message.state_version = snapshot.state_version
        message.round_id = snapshot.round_id or ''
        message.mode = {
            'easy': GameStateSnapshot.EASY, 'beginner': GameStateSnapshot.BEGINNER,
            'standard': GameStateSnapshot.STANDARD, 'challenge': GameStateSnapshot.CHALLENGE,
            'spatial': GameStateSnapshot.SPATIAL,
        }.get(snapshot.mode, GameStateSnapshot.EASY)
        message.game_state = snapshot.game_state
        message.has_origin = snapshot.origin_cell is not None
        if snapshot.origin_cell is not None:
            message.origin_column = snapshot.origin_cell.column
            message.origin_row = snapshot.origin_cell.row
        message.rotation_deg = snapshot.rotation_deg or 0
        message.handedness = (
            GameStateSnapshot.LEFT if snapshot.handedness == 'left' else GameStateSnapshot.RIGHT
        )
        message.has_target_visual_kind = snapshot.target_visual_kind is not None
        if snapshot.target_visual_kind is not None:
            message.target_visual_kind = self._cube_message_kind(snapshot.target_visual_kind)
        message.has_target_coordinate = snapshot.target_coordinate is not None
        if snapshot.target_coordinate is not None:
            message.target_game_x = snapshot.target_coordinate.x
            message.target_game_y = snapshot.target_coordinate.y
        message.cubes = [self._cube_message(cube) for cube in snapshot.cubes]
        message.answer_order = list(snapshot.answer_order)
        message.selected_answer_ids = list(snapshot.selected_answer_ids)
        message.disabled_answer_ids = list(snapshot.disabled_answer_ids)
        message.attempts_remaining = snapshot.attempts_remaining
        message.robot_operation_state = {
            'idle': GameStateSnapshot.OPERATION_IDLE,
            'executing': GameStateSnapshot.OPERATION_EXECUTING,
            'reconciliation_required': GameStateSnapshot.OPERATION_RECONCILIATION_REQUIRED,
        }[snapshot.operation_state]
        message.pending_request_id = snapshot.pending_request_id or ''
        message.pending_operation_id = snapshot.pending_operation_id or ''
        stages = (
            'PLANNING', 'MOVING_TO_PREGRASP', 'DESCENDING', 'GRASPING',
            'LIFTING', 'MOVING_TO_DESTINATION', 'RELEASING', 'RETREATING',
        )
        message.motion_stage = (
            stages.index(snapshot.motion_stage)
            if snapshot.motion_stage in stages else 0
        )
        message.game_flow_ready = snapshot.game_flow_ready
        message.recoverable_error = self._error_message(
            snapshot.error_code, snapshot.error_summary, snapshot
        )
        return message

    @staticmethod
    def _cube_message_kind(kind) -> int:
        return {
            'red': CubeState.RED,
            'green': CubeState.GREEN,
            'blue': CubeState.BLUE,
            'black': CubeState.BLACK,
            'white': CubeState.WHITE,
        }[kind.value]

    @classmethod
    def _cube_message(cls, cube) -> CubeState:
        message = CubeState()
        message.cube_id = cube.cube_id
        message.visual_kind = cls._cube_message_kind(cube.kind)
        message.column = cube.cell.column
        message.row = cube.cell.row
        message.game_x = cube.game_coordinate.x
        message.game_y = cube.game_coordinate.y
        message.removed = cube.removed
        return message

    @staticmethod
    def _error_message(code, summary, snapshot) -> ErrorSummary:
        message = ErrorSummary()
        message.code = int(code)
        message.summary = summary
        message.recoverable = code is not ExecutionErrorCode.NONE
        message.physical_progress = int(snapshot.physical_progress)
        return message
