"""FastAPI transport over browser DTOs and an allowlisted application backend."""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Callable, Optional, Protocol

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .auth import OperatorAuthorizer
from .dto import BrowserIntentResult, BrowserSnapshot
from .ros_bridge import BridgeUnavailable, RosApplicationBridge
from .text import load_child_text


class BrowserBackend(Protocol):
    """The deliberately small backend used by the HTTP and WebSocket transport."""

    async def invoke(self, name: str, **values: Any) -> Any: ...

    def add_snapshot_listener(
        self, callback: Callable[[BrowserSnapshot], None]
    ) -> Callable[[], None]: ...


class RosBrowserBackend:
    """Async façade over the thread-confined :class:`RosApplicationBridge`."""

    def __init__(self, bridge: RosApplicationBridge) -> None:
        self.bridge = bridge

    def start(self) -> None:
        self.bridge.start()

    def shutdown(self) -> None:
        self.bridge.shutdown()

    async def invoke(self, name: str, **values: Any) -> Any:
        return await asyncio.wrap_future(self.bridge.request(name, **values))

    def add_snapshot_listener(
        self, callback: Callable[[BrowserSnapshot], None]
    ) -> Callable[[], None]:
        return self.bridge.add_snapshot_listener(callback)


class SnapshotRelay:
    """Move snapshot notifications safely from ROS thread to FastAPI's event loop."""

    def __init__(self) -> None:
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._condition = asyncio.Condition()
        self._latest: Optional[BrowserSnapshot] = None

    def connect_loop(self) -> None:
        """Bind this relay to the running FastAPI event loop at application startup."""
        self._loop = asyncio.get_running_loop()

    def receive_from_backend(self, snapshot: BrowserSnapshot) -> None:
        """Accept a ROS-thread callback without touching asyncio objects in that thread."""
        if self._loop is not None:
            self._loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self._publish(snapshot))
            )

    async def _publish(self, snapshot: BrowserSnapshot) -> None:
        async with self._condition:
            if self._latest is None or snapshot.version >= self._latest.version:
                self._latest = snapshot
                self._condition.notify_all()

    async def current(self, backend: BrowserBackend) -> BrowserSnapshot:
        """Fetch a complete backend snapshot; a cache never fabricates game state."""
        snapshot = await backend.invoke('get_state')
        if not isinstance(snapshot, BrowserSnapshot):
            raise BridgeUnavailable('backend returned an invalid state snapshot')
        await self._publish(snapshot)
        return snapshot

    async def newer_than(self, version: int) -> BrowserSnapshot:
        """Wait for a strictly newer complete snapshot for one WebSocket client."""
        async with self._condition:
            await self._condition.wait_for(
                lambda: self._latest is not None and self._latest.version > version
            )
            assert self._latest is not None
            return self._latest


class RequestId(BaseModel):
    """Common browser mutation identity; the backend remains idempotency authority."""

    request_id: str = Field(min_length=1, max_length=128)


class GenerateRoundRequest(RequestId):
    mode: str
    seed: Optional[int] = None


class RoundRequest(RequestId):
    round_id: str = Field(min_length=1, max_length=128)


class SelectionRequest(RoundRequest):
    cube_id: str = Field(min_length=1, max_length=128)


class OperationRequest(RoundRequest):
    operation_id: str = Field(min_length=1, max_length=128)


class ReconcileRequest(OperationRequest):
    resolution: str


class CalibrationPointRequest(RequestId):
    point_name: str


class TeachCaptureRequest(RequestId):
    name: str
    kind: str
    destination_type: str = ''


class TeachNameRequest(RequestId):
    name: str


def create_app(
    backend: BrowserBackend,
    child_text: dict[str, Any],
    *,
    operator_token: str,
    web_dist_path: Optional[str] = None,
    start_backend: Optional[Callable[[], None]] = None,
    stop_backend: Optional[Callable[[], None]] = None,
) -> FastAPI:
    """Create the application transport; browser requests never receive ROS objects."""
    relay = SnapshotRelay()
    unsubscribe: Optional[Callable[[], None]] = None

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        nonlocal unsubscribe
        relay.connect_loop()
        if start_backend is not None:
            start_backend()
        unsubscribe = backend.add_snapshot_listener(relay.receive_from_backend)
        try:
            yield
        finally:
            if unsubscribe is not None:
                unsubscribe()
            if stop_backend is not None:
                stop_backend()

    app = FastAPI(title='Robots and Cubes application gateway', lifespan=lifespan)
    authorizer = OperatorAuthorizer(operator_token)

    async def call(name: str, **values: Any) -> Any:
        try:
            return await backend.invoke(name, **values)
        except BridgeUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    def response(result: BrowserIntentResult) -> dict[str, Any]:
        payload = result.to_dict()
        if not result.accepted:
            return payload
        return payload

    @app.get('/api/state')
    async def get_state() -> dict[str, Any]:
        return (await relay.current(backend)).to_dict()

    @app.get('/api/kid/text')
    async def get_kid_text() -> dict[str, Any]:
        return child_text

    @app.get('/api/operator/session')
    async def operator_session(
        _operator: None = Depends(authorizer.require_operator),
    ) -> dict[str, bool]:
        """Verify a bearer token without depending on optional ROS services."""
        return {'authorized': True}

    @app.post('/api/rounds')
    async def generate_round(
        request: GenerateRoundRequest,
        _operator: None = Depends(authorizer.require_operator),
    ) -> dict[str, Any]:
        modes = {
            'easy': 0, 'beginner': 1, 'standard': 2,
            'challenge': 3, 'spatial': 4,
        }
        if request.mode not in modes:
            raise HTTPException(status_code=422, detail='unsupported mode')
        result = await call(
            'generate_round', request_id=request.request_id, mode=modes[request.mode],
            use_explicit_seed=request.seed is not None, seed=request.seed or 0,
        )
        return response(result)

    @app.post('/api/rounds/confirm-setup')
    async def confirm_setup(
        request: RoundRequest, _operator: None = Depends(authorizer.require_operator)
    ) -> dict[str, Any]:
        return response(await call('confirm_setup', **request.model_dump()))

    @app.post('/api/rounds/selections')
    async def submit_selection(request: SelectionRequest) -> dict[str, Any]:
        return response(await call('submit_selection', **request.model_dump()))

    @app.post('/api/operations/retry')
    async def retry_operation(
        request: OperationRequest, _operator: None = Depends(authorizer.require_operator)
    ) -> dict[str, Any]:
        return response(await call('retry_operation', **request.model_dump()))

    @app.post('/api/operations/reconcile')
    async def reconcile_operation(
        request: ReconcileRequest, _operator: None = Depends(authorizer.require_operator)
    ) -> dict[str, Any]:
        resolutions = {'retry_safe': 0, 'cube_held_or_transported': 1,
                       'cube_at_destination': 2, 'abort_required': 3}
        if request.resolution not in resolutions:
            raise HTTPException(status_code=422, detail='unsupported reconciliation resolution')
        values = request.model_dump(exclude={'resolution'})
        values['resolution'] = resolutions[request.resolution]
        return response(await call('reconcile_operation', **values))

    @app.post('/api/rounds/abort')
    async def abort_round(
        request: RoundRequest, _operator: None = Depends(authorizer.require_operator)
    ) -> dict[str, Any]:
        return response(await call('abort_round', **request.model_dump()))

    @app.get('/api/calibration')
    async def calibration_status(
        _operator: None = Depends(authorizer.require_operator)
    ) -> Any:
        return await call('get_calibration_status')

    @app.post('/api/calibration/start')
    async def start_calibration(
        request: RequestId, _operator: None = Depends(authorizer.require_operator)
    ) -> Any:
        return await call('start_calibration', **request.model_dump())

    @app.post('/api/calibration/capture')
    async def capture_calibration(
        request: CalibrationPointRequest,
        _operator: None = Depends(authorizer.require_operator),
    ) -> Any:
        return await call('capture_calibration_point', **request.model_dump())

    @app.post('/api/calibration/validate')
    async def validate_calibration(
        request: RequestId, _operator: None = Depends(authorizer.require_operator)
    ) -> Any:
        return await call('validate_calibration', **request.model_dump())

    @app.post('/api/calibration/accept')
    async def accept_calibration(
        request: RequestId, _operator: None = Depends(authorizer.require_operator)
    ) -> Any:
        return await call('accept_calibration', **request.model_dump())

    @app.post('/api/calibration/cancel')
    async def cancel_calibration(
        request: RequestId, _operator: None = Depends(authorizer.require_operator)
    ) -> Any:
        return await call('cancel_calibration', **request.model_dump())

    @app.get('/api/teaching')
    async def list_teaching(
        _operator: None = Depends(authorizer.require_operator)
    ) -> Any:
        return await call('list_taught_positions')

    @app.post('/api/teaching/capture')
    async def capture_teaching(
        request: TeachCaptureRequest, _operator: None = Depends(authorizer.require_operator)
    ) -> Any:
        return await call('capture_taught_position', **request.model_dump())

    @app.post('/api/teaching/accept')
    async def accept_teaching(
        request: TeachNameRequest, _operator: None = Depends(authorizer.require_operator)
    ) -> Any:
        return await call('accept_taught_position', **request.model_dump())

    @app.post('/api/teaching/delete')
    async def delete_teaching(
        request: TeachNameRequest, _operator: None = Depends(authorizer.require_operator)
    ) -> Any:
        return await call('delete_taught_position', **request.model_dump())

    @app.websocket('/api/ws')
    async def websocket_state(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            snapshot = await relay.current(backend)
            await websocket.send_json({'type': 'snapshot', 'snapshot': snapshot.to_dict()})
            version = snapshot.version
            while True:
                snapshot = await relay.newer_than(version)
                version = snapshot.version
                await websocket.send_json({'type': 'snapshot', 'snapshot': snapshot.to_dict()})
        except WebSocketDisconnect:
            return

    if web_dist_path:
        _mount_web_application(app, web_dist_path)
    return app


def _mount_web_application(app: FastAPI, web_dist_path: str) -> None:
    """Serve built SPA entry routes without placing static files above ``/api``."""
    index_path = f'{web_dist_path}/index.html'

    @app.get('/')
    @app.get('/kid')
    @app.get('/operator')
    async def web_application() -> FileResponse:
        """Serve the one React entry document for each supported browser route."""
        return FileResponse(index_path)

    app.mount('/assets', StaticFiles(directory=f'{web_dist_path}/assets'), name='assets')


def create_ros_app(
    rows: int, columns: int, child_text_path: str, operator_token: str,
    web_dist_path: Optional[str] = None,
) -> FastAPI:
    """Wire production FastAPI transport to the dedicated ROS executor thread."""
    bridge = RosApplicationBridge(rows, columns)
    backend = RosBrowserBackend(bridge)
    return create_app(
        backend, load_child_text(child_text_path), operator_token=operator_token,
        start_backend=backend.start,
        stop_backend=backend.shutdown,
        web_dist_path=web_dist_path,
    )
