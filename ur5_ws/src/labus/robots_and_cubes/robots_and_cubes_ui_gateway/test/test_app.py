# flake8: noqa
"""Hardware-free HTTP/WebSocket application transport tests."""

import asyncio
from pathlib import Path

import pytest

fastapi = pytest.importorskip('fastapi')
pytest.importorskip('httpx')
import httpx

from robots_and_cubes_ui_gateway.app import SnapshotRelay, create_app
from robots_and_cubes_ui_gateway.dto import BrowserCube, BrowserIntentResult, BrowserSnapshot
from robots_and_cubes_ui_gateway.text import load_child_text


def _snapshot(version=1, ready=False):
    return BrowserSnapshot(
        schema_version=1, version=version, round_id='round-1', mode='standard',
        game_state='WAITING_FOR_PHYSICAL_SETUP', board={'rows': 6, 'columns': 6},
        origin={'column': 2, 'row': 2, 'rotation_deg': 0, 'handedness': 'right'},
        target_visual_kind=None, target_coordinate=None,
        cubes=(BrowserCube('green-1', 'green', '★', 3, 3, {'x': 1, 'y': 1}, False),),
        answer_order=('green-1',), selected_answer_ids=(), disabled_answer_ids=(),
        attempts_remaining=2, readiness={'game_flow_ready': ready}, motion_stage=None,
        operation={'state': 'idle', 'request_id': None, 'id': None}, recoverable_error=None,
    )


class FakeBackend:
    def __init__(self):
        self.snapshot = _snapshot()
        self.calls = []
        self.listeners = []

    async def invoke(self, name, **values):
        self.calls.append((name, values))
        if name == 'get_state':
            return self.snapshot
        return BrowserIntentResult(True, self.snapshot, name == 'submit_selection')

    def add_snapshot_listener(self, callback):
        self.listeners.append(callback)
        return lambda: self.listeners.remove(callback)

    def emit(self, snapshot):
        self.snapshot = snapshot
        for callback in tuple(self.listeners):
            callback(snapshot)


def _app(backend):
    text_path = Path(__file__).parents[2] / 'config' / 'child_text_hr.yaml'
    return create_app(backend, load_child_text(text_path), operator_token='test-token')


def test_state_and_mutations_are_allowlisted_and_retain_backend_identity():
    backend = FakeBackend()
    async def exercise():
        transport = httpx.ASGITransport(app=_app(backend))
        async with httpx.AsyncClient(transport=transport, base_url='http://gateway') as client:
            assert (await client.get('/api/state')).json()['round_id'] == 'round-1'
            return (await client.post('/api/rounds/selections', json={
                'request_id': 'kid-1', 'round_id': 'round-1', 'cube_id': 'green-1',
            })).json()
    payload = asyncio.run(exercise())
    assert payload['accepted'] is True
    assert backend.calls[-1] == ('submit_selection', {
        'request_id': 'kid-1', 'round_id': 'round-1', 'cube_id': 'green-1',
    })


def test_state_relay_supplies_full_snapshot_then_newer_version_after_reconnect():
    backend = FakeBackend()
    async def exercise():
        relay = SnapshotRelay()
        relay.connect_loop()
        first = await relay.current(backend)
        waiting = asyncio.create_task(relay.newer_than(first.version))
        backend.snapshot = _snapshot(version=2, ready=True)
        relay.receive_from_backend(backend.snapshot)
        second = await waiting
        reconnect = await relay.current(backend)
        return first, second, reconnect
    first, second, reconnect = asyncio.run(exercise())
    assert first.version == 1
    assert second.version == 2
    assert reconnect.version == 2


def test_concurrent_requests_keep_distinct_request_ids():
    backend = FakeBackend()
    async def exercise():
        await asyncio.gather(*[
            backend.invoke('generate_round', request_id=f'operator-{index}')
            for index in range(20)
        ])
    asyncio.run(exercise())
    assert {values['request_id'] for _, values in backend.calls} == {
        f'operator-{index}' for index in range(20)
    }


def test_operator_intents_require_server_side_bearer_authorization():
    backend = FakeBackend()

    async def exercise():
        transport = httpx.ASGITransport(app=_app(backend))
        async with httpx.AsyncClient(transport=transport, base_url='http://gateway') as client:
            denied = await client.post('/api/rounds', json={'request_id': 'one', 'mode': 'standard'})
            allowed = await client.post(
                '/api/rounds', headers={'Authorization': 'Bearer test-token'},
                json={'request_id': 'two', 'mode': 'standard'},
            )
            kid_allowed = await client.post('/api/rounds/selections', json={
                'request_id': 'three', 'round_id': 'round-1', 'cube_id': 'green-1',
            })
            return denied.status_code, allowed.status_code, kid_allowed.status_code

    assert asyncio.run(exercise()) == (401, 200, 200)


def test_operator_session_checks_only_the_server_side_bearer_token():
    backend = FakeBackend()

    async def exercise():
        transport = httpx.ASGITransport(app=_app(backend))
        async with httpx.AsyncClient(transport=transport, base_url='http://gateway') as client:
            denied = await client.get('/api/operator/session')
            allowed = await client.get(
                '/api/operator/session', headers={'Authorization': 'Bearer test-token'},
            )
            return denied.status_code, allowed.status_code, allowed.json(), backend.calls

    assert asyncio.run(exercise()) == (401, 200, {'authorized': True}, [])


def test_built_react_entry_routes_and_assets_are_served_without_shadowing_api():
    backend = FakeBackend()
    dist = Path(__file__).parents[2] / 'web' / 'robots_and_cubes_web' / 'dist'
    app = create_app(
        backend, load_child_text(Path(__file__).parents[2] / 'config' / 'child_text_hr.yaml'),
        operator_token='test-token', web_dist_path=str(dist),
    )
    paths = {route.path for route in app.routes}
    assert {'/api/state', '/api/ws', '/kid', '/operator', '/assets'} <= paths
    assert (dist / 'index.html').is_file()
    assert list((dist / 'assets').glob('*.js'))
    assert list((dist / 'assets').glob('*.css'))
