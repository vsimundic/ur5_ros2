"""Start only the hardware-free Robots and Cubes backend application mock."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """Launch a game manager and ExecutePickPlace mock, never a robot stack."""
    settings = LaunchConfiguration('user_settings_path')
    events = LaunchConfiguration('event_log_path')
    child_text = LaunchConfiguration('child_text_path')
    gateway_host = LaunchConfiguration('gateway_host')
    gateway_port = LaunchConfiguration('gateway_port')
    web_dist = LaunchConfiguration('web_dist_path')
    disabled = LaunchConfiguration('disabled_cells')
    mode = LaunchConfiguration('execution_mode')
    return LaunchDescription([
        DeclareLaunchArgument(
            'user_settings_path',
            description='Explicit editable Robots and Cubes user_settings.yaml path.',
        ),
        DeclareLaunchArgument(
            'event_log_path',
            description='Explicit JSONL event log path for this mock session.',
        ),
        DeclareLaunchArgument(
            'child_text_path',
            description='Explicit UTF-8 Croatian child_text_hr.yaml path for the UI gateway.',
        ),
        DeclareLaunchArgument(
            'gateway_host', default_value='127.0.0.1',
            description='Use 0.0.0.0 only for a supervised local-network display.',
        ),
        DeclareLaunchArgument('gateway_port', default_value='8080'),
        DeclareLaunchArgument(
            'web_dist_path', default_value='',
            description='Optional built React distribution directory served by the gateway.',
        ),
        DeclareLaunchArgument(
            'disabled_cells', default_value='',
            description='Optional YAML-style disabled mock cells, for example ["0,0"].',
        ),
        DeclareLaunchArgument(
            'execution_mode', default_value='MOCK',
            description='Must remain MOCK; PLAN_ONLY and REAL intentionally fail closed.',
        ),
        Node(
            package='robots_and_cubes_mock_execution',
            executable='mock_game_manager',
            name='robots_and_cubes_game_manager',
            parameters=[{
                'user_settings_path': settings,
                'event_log_path': events,
                'disabled_cells': disabled,
                'execution_mode': mode,
            }],
        ),
        Node(
            package='robots_and_cubes_mock_execution',
            executable='mock_execute_pick_place',
            name='robots_and_cubes_mock_execute_pick_place',
            parameters=[{
                'user_settings_path': settings,
                'disabled_cells': disabled,
                'execution_mode': mode,
            }],
        ),
        Node(
            package='robots_and_cubes_ui_gateway',
            executable='ui_gateway',
            name='robots_and_cubes_ui_gateway',
            parameters=[{
                'user_settings_path': settings,
                'child_text_path': child_text,
                'host': gateway_host,
                'port': gateway_port,
                'web_dist_path': web_dist,
            }],
        ),
    ])
