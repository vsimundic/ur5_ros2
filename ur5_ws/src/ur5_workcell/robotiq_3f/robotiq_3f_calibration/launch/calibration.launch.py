# Copyright 2026 UR5 ROS 2 maintainers

"""Launch the isolated Robotiq 3F calibration GUI and RViz view."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    """Create the visualization-only calibration application."""
    package_share = Path(
        get_package_share_directory('robotiq_3f_calibration')
    )
    xacro_file = package_share / 'urdf' / 'calibration_gripper.urdf.xacro'
    rviz_config = package_share / 'rviz' / 'calibration.rviz'

    output_file = LaunchConfiguration('output_file')
    status_topic = LaunchConfiguration('status_topic')
    clicked_point_topic = LaunchConfiguration('clicked_point_topic')
    robot_description = ParameterValue(
        Command([FindExecutable(name='xacro'), ' ', str(xacro_file)]),
        value_type=str,
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'output_file',
            default_value=(
                '/workspaces/ur5_ros2/gripper_calibration/'
                'gripper_samples.csv'
            ),
            description='CSV file created or appended by Record sample.',
        ),
        DeclareLaunchArgument(
            'status_topic', default_value='/robotiq_3f/status'
        ),
        DeclareLaunchArgument(
            'clicked_point_topic', default_value='/clicked_point'
        ),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_description}],
            output='screen',
        ),
        Node(
            package='robotiq_3f_calibration',
            executable='calibration_gui',
            parameters=[{
                'output_file': output_file,
                'status_topic': status_topic,
                'clicked_point_topic': clicked_point_topic,
            }],
            output='screen',
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', str(rviz_config)],
            output='screen',
        ),
    ])
