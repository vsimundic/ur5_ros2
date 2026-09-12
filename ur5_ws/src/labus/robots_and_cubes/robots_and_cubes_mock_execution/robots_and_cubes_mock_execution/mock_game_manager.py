"""Mock-only game-manager entry point with synthetic readiness and event logging."""

from pathlib import Path

import rclpy
from rclpy.node import Node

from robots_and_cubes_config import load_user_settings
from robots_and_cubes_game.event_log import JsonlEventLogger
from robots_and_cubes_game.ros_game_manager import RosGameManagerNode

from .readiness import SyntheticMockReadiness


def _disabled_cells(value) -> tuple[tuple[int, int], ...]:
    """Parse synthetic-only cell exclusions provided by mock launch/test tooling."""
    if not value or value == '[]':
        return ()
    values = [value] if isinstance(value, str) else value
    return tuple(tuple(int(part) for part in item.split(',', 1)) for item in values)


def _configuration() -> tuple[object, Path, tuple[tuple[int, int], ...]]:
    """Read explicit mock-only launch settings without loading calibration/teaching data."""
    bootstrap = Node('robots_and_cubes_mock_game_configuration')
    try:
        settings_path = bootstrap.declare_parameter('user_settings_path', '').value
        event_path = bootstrap.declare_parameter('event_log_path', '').value
        disabled = bootstrap.declare_parameter('disabled_cells', '').value
        mode = bootstrap.declare_parameter('execution_mode', 'MOCK').value
    finally:
        bootstrap.destroy_node()
    if not settings_path or not event_path:
        raise RuntimeError('user_settings_path and event_log_path are required in mock mode')
    if mode != 'MOCK':
        raise RuntimeError(f'execution mode {mode!r} is unsupported; mock is MOCK only')
    settings = load_user_settings(Path(settings_path))
    if settings.execution_mode != 'MOCK':
        raise RuntimeError('application.execution_mode must be MOCK for mock launch')
    return settings, Path(event_path), _disabled_cells(disabled)


def main() -> None:
    """Run the manager in MOCK mode; synthetic readiness cannot enable REAL mode."""
    rclpy.init()
    try:
        settings, event_path, disabled = _configuration()
        readiness = SyntheticMockReadiness(settings, frozenset(disabled))
        node = RosGameManagerNode(
            settings,
            configuration_revision='SYNTHETIC_MOCK_CONFIGURATION_ONLY',
            calibration_revision=readiness.calibration_id,
            event_writer=JsonlEventLogger(event_path).write,
            preflight=readiness.preflight,
        )
        try:
            rclpy.spin(node)
        finally:
            node.destroy_node()
    finally:
        rclpy.shutdown()
