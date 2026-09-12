"""Developer utility for exercising a running hardware-free mock backend."""

import sys
import time
from uuid import uuid4

import rclpy
from rclpy.node import Node

from robots_and_cubes_interfaces.msg import CubeState, GameStateSnapshot
from robots_and_cubes_interfaces.srv import (
    ConfirmPhysicalSetup,
    GenerateRound,
    GetGameState,
    SubmitChildSelection,
)


class MockBackendSmokeClient(Node):
    """Drive the normal service boundary; it has no access to hardware endpoints."""

    def __init__(self) -> None:
        """Create only application service clients for a pre-started mock backend."""
        super().__init__('robots_and_cubes_mock_smoke_client')
        self._generate = self.create_client(GenerateRound, 'generate_round')
        self._confirm = self.create_client(ConfirmPhysicalSetup, 'confirm_physical_setup')
        self._selection = self.create_client(SubmitChildSelection, 'submit_child_selection')
        self._state = self.create_client(GetGameState, 'get_game_state')

    def call(self, client, request):
        """Wait for an application service and return its bounded response."""
        if not client.wait_for_service(timeout_sec=5.0):
            raise RuntimeError(f'application service unavailable: {client.srv_name}')
        future = client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
        if not future.done() or future.exception() is not None:
            raise RuntimeError(f'application service did not complete: {client.srv_name}')
        return future.result()

    def run(self) -> GameStateSnapshot:
        """Generate, set up, select green, and wait for the mock success snapshot."""
        generate = GenerateRound.Request()
        generate.request_id = str(uuid4())
        generate.mode = GenerateRound.Request.STANDARD
        generate.use_explicit_seed = True
        generate.seed = 8
        round_response = self.call(self._generate, generate)
        if not round_response.accepted:
            raise RuntimeError(round_response.error.summary)

        confirm = ConfirmPhysicalSetup.Request()
        confirm.request_id = str(uuid4())
        confirm.round_id = round_response.snapshot.round_id
        setup_response = self.call(self._confirm, confirm)
        if not setup_response.accepted:
            raise RuntimeError(setup_response.error.summary)

        snapshot = self.call(self._state, GetGameState.Request()).snapshot
        green = next(
            cube.cube_id for cube in snapshot.cubes
            if cube.visual_kind == CubeState.GREEN
        )
        selection = SubmitChildSelection.Request()
        selection.request_id = str(uuid4())
        selection.round_id = snapshot.round_id
        selection.cube_id = green
        selection_response = self.call(self._selection, selection)
        if not selection_response.accepted:
            raise RuntimeError(selection_response.error.summary)

        for _ in range(100):
            snapshot = self.call(self._state, GetGameState.Request()).snapshot
            if snapshot.game_state == 'success':
                return snapshot
            time.sleep(0.05)
        raise RuntimeError('mock operation did not reach success within five seconds')


def main() -> None:
    """Exit zero after a complete Standard mock round, otherwise explain the failure."""
    rclpy.init()
    client = MockBackendSmokeClient()
    try:
        snapshot = client.run()
        print(f'mock backend success: state version {snapshot.state_version}')
    except RuntimeError as error:
        print(f'mock backend smoke test failed: {error}', file=sys.stderr)
        raise SystemExit(1) from error
    finally:
        client.destroy_node()
        rclpy.shutdown()
