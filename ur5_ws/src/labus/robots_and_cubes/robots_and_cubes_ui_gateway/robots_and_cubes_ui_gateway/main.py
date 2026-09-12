"""Console entry point for the hardware-safe Robots and Cubes web gateway."""

import os
from pathlib import Path

from robots_and_cubes_config import load_user_settings
import uvicorn

from .app import create_ros_app


def main() -> None:
    """Serve only application UI transport; starting it never starts robot hardware."""
    import rclpy
    from rclpy.node import Node

    rclpy.init()
    bootstrap = Node('robots_and_cubes_ui_gateway_configuration')
    try:
        settings_path = bootstrap.declare_parameter('user_settings_path', '').value
        child_text_path = bootstrap.declare_parameter('child_text_path', '').value
        web_dist_path = bootstrap.declare_parameter('web_dist_path', '').value
        host = bootstrap.declare_parameter('host', '127.0.0.1').value
        port = bootstrap.declare_parameter('port', 8080).value
        operator_token_env = bootstrap.declare_parameter(
            'operator_token_env', 'ROBOTS_AND_CUBES_OPERATOR_TOKEN'
        ).value
    finally:
        bootstrap.destroy_node()
        rclpy.shutdown()
    if not settings_path or not child_text_path:
        raise RuntimeError('user_settings_path and child_text_path are required')
    operator_token = os.environ.get(operator_token_env, '')
    if not operator_token:
        raise RuntimeError(
            f'operator token environment variable {operator_token_env!r} is required'
        )
    settings = load_user_settings(Path(settings_path))
    app = create_ros_app(
        settings.board.rows, settings.board.columns, child_text_path, operator_token,
        web_dist_path or None,
    )
    uvicorn.run(app, host=host, port=int(port), log_level='info')
