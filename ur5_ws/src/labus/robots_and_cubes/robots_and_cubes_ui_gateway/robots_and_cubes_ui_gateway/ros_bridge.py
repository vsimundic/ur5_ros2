"""Thread-confined ROS adapter for the small, approved browser API surface."""

from concurrent.futures import Future
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Event, Lock, Thread
from typing import Any, Callable, Optional

from .dto import BrowserSnapshot, intent_from_ros, snapshot_from_ros


class BridgeUnavailable(RuntimeError):
    """An approved application service is unavailable or the bridge is stopping."""


@dataclass(frozen=True)
class _Request:
    """A web-thread request that only the ROS executor thread may initiate."""

    name: str
    values: dict[str, Any]
    result: Future


class RosApplicationBridge:
    """
    Own every rclpy object on one executor thread.

    FastAPI workers place typed allowlisted requests onto a queue.  The executor
    thread owns the clients, calls ``call_async``, converts results to browser
    DTOs, and invokes snapshot listeners.  No browser thread reaches a ROS
    client, executor, topic, parameter, controller, or action object.
    """

    _SERVICE_TYPES: dict[str, tuple[str, str]] = {
        'get_state': ('GetGameState', 'get_game_state'),
        'generate_round': ('GenerateRound', 'generate_round'),
        'confirm_setup': ('ConfirmPhysicalSetup', 'confirm_physical_setup'),
        'submit_selection': ('SubmitChildSelection', 'submit_child_selection'),
        'retry_operation': ('RetryOperation', 'retry_operation'),
        'reconcile_operation': ('ReconcileOperation', 'reconcile_operation'),
        'abort_round': ('AbortRound', 'abort_round'),
        'get_calibration_status': ('GetCalibrationStatus', 'get_calibration_status'),
        'start_calibration': ('StartGridCalibration', 'start_grid_calibration'),
        'capture_calibration_point': ('CaptureCalibrationPoint', 'capture_calibration_point'),
        'validate_calibration': ('ValidateGridCalibration', 'validate_grid_calibration'),
        'accept_calibration': ('AcceptGridCalibration', 'accept_grid_calibration'),
        'cancel_calibration': ('CancelGridCalibration', 'cancel_grid_calibration'),
        'capture_taught_position': ('CaptureTaughtPosition', 'capture_taught_position'),
        'accept_taught_position': ('AcceptTaughtPosition', 'accept_taught_position'),
        'delete_taught_position': ('DeleteTaughtPosition', 'delete_taught_position'),
        'list_taught_positions': ('ListTaughtPositions', 'list_taught_positions'),
    }

    def __init__(self, rows: int, columns: int) -> None:
        self._rows = rows
        self._columns = columns
        self._queue: Queue[_Request] = Queue()
        self._ready = Event()
        self._stopped = Event()
        self._thread: Optional[Thread] = None
        self._startup_error: Optional[BaseException] = None
        self._listeners: list[Callable[[BrowserSnapshot], None]] = []
        self._listener_lock = Lock()
        self._latest: Optional[BrowserSnapshot] = None

    def start(self) -> None:
        """Create the private ROS context/executor thread and wait for readiness."""
        if self._thread is not None:
            return
        self._thread = Thread(target=self._run, name='robots-and-cubes-ros', daemon=False)
        self._thread.start()
        self._ready.wait(timeout=5.0)
        if self._startup_error is not None:
            raise BridgeUnavailable(str(self._startup_error)) from self._startup_error
        if not self._ready.is_set():
            raise BridgeUnavailable('ROS bridge startup timed out')

    def shutdown(self) -> None:
        """Stop spinning, fail queued web requests, and join the executor thread."""
        self._stopped.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                raise RuntimeError('ROS bridge executor did not stop')
            self._thread = None
        self._fail_queued('ROS bridge is shut down')

    def add_snapshot_listener(
        self, listener: Callable[[BrowserSnapshot], None]
    ) -> Callable[[], None]:
        """Register a transport callback and return its safe unsubscribe operation."""
        with self._listener_lock:
            self._listeners.append(listener)
        if self._latest is not None:
            listener(self._latest)

        def remove() -> None:
            with self._listener_lock:
                if listener in self._listeners:
                    self._listeners.remove(listener)
        return remove

    def latest_snapshot(self) -> Optional[BrowserSnapshot]:
        """Return the latest complete subscription snapshot, if one has arrived."""
        return self._latest

    def request(self, name: str, **values: Any) -> Future:
        """Queue one named API operation; arbitrary ROS service names are impossible."""
        if name not in self._SERVICE_TYPES:
            raise ValueError(f'unsupported browser operation: {name}')
        result: Future = Future()
        if self._stopped.is_set() or self._thread is None:
            result.set_exception(BridgeUnavailable('ROS bridge is not running'))
        else:
            self._queue.put(_Request(name, values, result))
        return result

    def _run(self) -> None:
        """Own all rclpy object creation, use, destruction, and spinning."""
        context = None
        node = None
        executor = None
        try:
            from rclpy.context import Context
            from rclpy.executors import SingleThreadedExecutor
            from rclpy.node import Node
            from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
            from robots_and_cubes_interfaces.msg import GameStateSnapshot
            from robots_and_cubes_interfaces import srv

            context = Context()
            context.init()
            node = Node('robots_and_cubes_ui_gateway_ros_bridge', context=context)
            executor = SingleThreadedExecutor(context=context)
            executor.add_node(node)
            services = {
                name: (node.create_client(getattr(srv, type_name), ros_name),
                       getattr(srv, type_name).Request)
                for name, (type_name, ros_name) in self._SERVICE_TYPES.items()
            }
            qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                             reliability=ReliabilityPolicy.RELIABLE)
            node.create_subscription(GameStateSnapshot, 'game_state', self._on_snapshot, qos)
            node.create_timer(0.01, lambda: self._drain(services))
            self._ready.set()
            while not self._stopped.is_set() and context.ok():
                executor.spin_once(timeout_sec=0.1)
        except BaseException as error:  # Surface startup/runtime bridge failures predictably.
            self._startup_error = error
            self._ready.set()
            self._fail_queued(str(error))
        finally:
            if executor is not None:
                executor.shutdown()
            if node is not None:
                node.destroy_node()
            if context is not None:
                context.shutdown()
            self._ready.set()
            self._fail_queued('ROS bridge stopped')

    def _drain(self, services: dict[str, Any]) -> None:
        """Initiate service calls exclusively from the ROS executor callback."""
        while True:
            try:
                request = self._queue.get_nowait()
            except Empty:
                return
            client, request_type = services[request.name]
            if not client.service_is_ready():
                request.result.set_exception(
                    BridgeUnavailable(f'application service {request.name} is unavailable')
                )
                continue
            ros_request = request_type()
            for field, value in request.values.items():
                setattr(ros_request, field, value)
            future = client.call_async(ros_request)
            future.add_done_callback(
                lambda completed, web_request=request: self._complete(web_request, completed)
            )

    def _complete(self, request: _Request, future: Any) -> None:
        """Convert only approved service responses before resolving a web request."""
        if request.result.cancelled():
            return
        try:
            response = future.result()
            if request.name == 'get_state':
                result: Any = snapshot_from_ros(response.snapshot, self._rows, self._columns)
            elif request.name == 'get_calibration_status':
                result = _calibration_status(response.status)
            elif request.name == 'list_taught_positions':
                result = [_taught_position(position) for position in response.positions]
            elif request.name.startswith(('start_calibration', 'capture_calibration',
                                          'validate_calibration', 'accept_calibration',
                                          'cancel_calibration')):
                result = _status_intent(response)
            elif request.name.startswith(('capture_taught', 'accept_taught')):
                result = _position_intent(response)
            elif request.name == 'delete_taught_position':
                result = _delete_intent(response)
            else:
                result = intent_from_ros(response, self._rows, self._columns)
            request.result.set_result(result)
        except Exception as error:
            request.result.set_exception(BridgeUnavailable(str(error)))

    def _on_snapshot(self, message: object) -> None:
        snapshot = snapshot_from_ros(message, self._rows, self._columns)
        self._latest = snapshot
        with self._listener_lock:
            listeners = tuple(self._listeners)
        for listener in listeners:
            listener(snapshot)

    def _fail_queued(self, summary: str) -> None:
        while True:
            try:
                request = self._queue.get_nowait()
            except Empty:
                return
            if not request.result.done():
                request.result.set_exception(BridgeUnavailable(summary))


def _calibration_status(status: object) -> dict[str, Any]:
    return {
        'state': int(status.state), 'active_valid': status.active_valid,
        'calibration_id': status.active_calibration_id or None,
        'reason': status.reason_code or None, 'captured_points': list(status.captured_points),
    }


def _error(error: object) -> Optional[dict[str, Any]]:
    if not error.code and not error.summary:
        return None
    return {'code': int(error.code), 'summary': error.summary,
            'recoverable': error.recoverable, 'physical_progress': int(error.physical_progress)}


def _status_intent(response: object) -> dict[str, Any]:
    return {'accepted': response.accepted, 'error': _error(response.error),
            'status': _calibration_status(response.status)}


def _taught_position(position: object) -> dict[str, Any]:
    return {'name': position.name, 'kind': position.kind, 'accepted': position.accepted,
            'frame_id': position.frame_id, 'destination_type': position.destination_type,
            'configuration_revision': position.configuration_revision}


def _position_intent(response: object) -> dict[str, Any]:
    return {'accepted': response.accepted, 'error': _error(response.error),
            'position': _taught_position(response.position)}


def _delete_intent(response: object) -> dict[str, Any]:
    return {'accepted': response.accepted, 'error': _error(response.error)}
