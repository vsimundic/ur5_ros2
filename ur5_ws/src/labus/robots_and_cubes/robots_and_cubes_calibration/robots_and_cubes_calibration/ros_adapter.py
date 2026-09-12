"""
Narrow, read-only ROS-boundary adapter for calibration and teaching.

The eventual rclpy node binds generated services to this class.  It has no
motion, gripper, planner, or arbitrary-TF command operation.  Its sole TF
publication is the accepted fixed ``base_link -> grid_frame`` transform.
"""

from pathlib import Path
from typing import Callable, Dict, Protocol

from .calibration_manager import CalibrationManager, MeasuredToolPose
from .persistence import save_atomic, save_calibration
from .teaching_manager import MeasuredCartesianPose, MeasuredJointState, TeachingManager


class StaticGridTransformPublisher(Protocol):
    """The one injected owner allowed to publish the accepted fixed grid frame."""

    def publish_grid_transform(self, transform: object) -> None:
        """Publish ``base_link -> grid_frame`` as a fixed transform."""


class CalibrationRosAdapter:
    """Translate narrow service operations into command-free domain calls."""

    def __init__(
        self,
        calibration: CalibrationManager,
        teaching: TeachingManager,
        tool_pose_provider: Callable[[], MeasuredToolPose],
        joint_state_provider: Callable[[], MeasuredJointState],
        cartesian_pose_provider: Callable[[], MeasuredCartesianPose],
        grid_transform_publisher: StaticGridTransformPublisher,
        calibration_path: Path,
        taught_poses_path: Path,
    ) -> None:
        self.calibration = calibration
        self.teaching = teaching
        self.tool_pose_provider = tool_pose_provider
        self.joint_state_provider = joint_state_provider
        self.cartesian_pose_provider = cartesian_pose_provider
        self.grid_transform_publisher = grid_transform_publisher
        self.calibration_path = calibration_path
        self.taught_poses_path = taught_poses_path
        self._completed_requests: Dict[str, object] = {}

    def _once(self, request_id: str, operation: Callable[[], object]) -> object:
        """Return the first mutation result for a repeated client request ID."""
        if request_id and request_id in self._completed_requests:
            return self._completed_requests[request_id]
        result = operation()
        if request_id:
            self._completed_requests[request_id] = result
        return result

    def start_calibration(self, request_id: str) -> object:
        """Start a draft; an active calibration remains in use."""
        return self._once(request_id, self.calibration.start)

    def capture_calibration_point(self, request_id: str, point_name: str) -> object:
        """Read fresh ``base_link -> tool0`` TF and capture its transformed pen tip."""
        return self._once(
            request_id,
            lambda: self.calibration.capture(point_name, self.tool_pose_provider()),
        )

    def validate_calibration(self, request_id: str) -> object:
        """Validate a draft without changing the active transform."""
        return self._once(request_id, self.calibration.validate)

    def accept_calibration(self, request_id: str) -> object:
        """Atomically persist, accept, then publish the fixed accepted grid frame."""
        def operation() -> object:
            accepted = self.calibration.accept(
                lambda record: save_calibration(self.calibration_path, record)
            )
            self.grid_transform_publisher.publish_grid_transform(accepted.transform)
            return accepted
        return self._once(request_id, operation)

    def cancel_calibration(self, request_id: str) -> object:
        """Discard only the draft candidate."""
        return self._once(request_id, self.calibration.cancel)

    def get_calibration_status(self) -> object:
        """Return lifecycle status without mutation."""
        return self.calibration.status()

    def capture_taught_joint_position(self, request_id: str, name: str) -> object:
        """Read and stage an actual fresh home/safe joint state."""
        return self._once(
            request_id,
            lambda: self.teaching.capture_joints(name, self.joint_state_provider()),
        )

    def capture_taught_destination(
        self, request_id: str, name: str, destination_type: str
    ) -> object:
        """Read and stage an actual fresh base_link Cartesian destination."""
        return self._once(
            request_id,
            lambda: self.teaching.capture_destination(
                name, destination_type, self.cartesian_pose_provider()
            ),
        )

    def accept_taught_position(self, request_id: str, name: str) -> object:
        """Accept then atomically write operator-taught data."""
        def operation() -> object:
            accepted = self.teaching.accept(
                name, lambda _value, data: save_atomic(self.taught_poses_path, data)
            )
            return accepted
        return self._once(request_id, operation)

    def delete_taught_position(self, request_id: str, name: str) -> object:
        """Delete one accepted teaching value and atomically update storage."""
        def operation() -> object:
            self.teaching.delete(name)
            self.teaching.save(self.taught_poses_path)
            return self.teaching.list_accepted()
        return self._once(request_id, operation)

    def list_taught_positions(self) -> object:
        """List accepted positions only."""
        return self.teaching.list_accepted()
