"""Launch the authoritative UR5 workcell in Gazebo Sim with optional MoveIt."""

import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    RegisterEventHandler,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, IfElseSubstitution, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    """Start Gazebo, ros2_control, robot state publication, and MoveIt."""
    sim_share = Path(get_package_share_directory('ur5_workcell_sim'))
    ros_gz_share = Path(get_package_share_directory('ros_gz_sim'))
    moveit_share = Path(
        get_package_share_directory('ur5_workcell_moveit_config')
    )
    gripper_controller_share = Path(
        get_package_share_directory('robotiq_3f_controller')
    )
    description_file = sim_share / 'urdf' / 'workcell_sim.urdf.xacro'
    controllers_file = sim_share / 'config' / 'ur_controllers.yaml'
    camera_bridge_file = sim_share / 'config' / 'camera_bridge.yaml'
    world_file = sim_share / 'worlds' / 'workcell.sdf'
    description_packages = [
        'realsense_l515_description',
        'robotiq_3f_description',
        'robotiq_ft300s_description',
        'xela_usp44_description',
    ]
    resource_paths = [
        str(Path(get_package_share_directory(package)).parent)
        for package in description_packages
    ]
    existing_resource_path = os.environ.get('GZ_SIM_RESOURCE_PATH')
    if existing_resource_path:
        resource_paths.append(existing_resource_path)

    robot_description_content = Command([
        'xacro ',
        str(description_file),
        ' name:=ur5_workcell',
        ' ur_type:=ur5',
        ' safety_limits:=true',
        ' simulation_controllers:=',
        str(controllers_file),
        ' simulate_camera:=',
        LaunchConfiguration('launch_camera'),
    ])
    robot_description = {
        'robot_description': ParameterValue(
            robot_description_content,
            value_type=str,
        )
    }

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'use_sim_time': True}, robot_description],
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(ros_gz_share / 'launch' / 'gz_sim.launch.py')
        ),
        launch_arguments={
            'gz_args': IfElseSubstitution(
                LaunchConfiguration('gazebo_gui'),
                if_value=[
                    '-r -v 4 --physics-engine ',
                    'gz-physics-bullet-featherstone-plugin ',
                    str(world_file),
                ],
                else_value=[
                    '-s -r -v 4 --physics-engine ',
                    'gz-physics-bullet-featherstone-plugin ',
                    str(world_file),
                ],
            ),
        }.items(),
    )

    spawn_workcell = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-string',
            robot_description_content,
            '-name',
            'ur5_workcell',
            '-allow_renaming',
            'false',
        ],
    )

    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen',
    )

    camera_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='camera_bridge',
        output='screen',
        condition=IfCondition(LaunchConfiguration('launch_camera')),
        parameters=[{'config_file': str(camera_bridge_file)}],
    )

    pointcloud_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='camera_pointcloud_bridge',
        output='screen',
        condition=IfCondition(LaunchConfiguration('camera_pointcloud')),
        arguments=[
            '/camera/sim_rgbd/points'
            '@sensor_msgs/msg/PointCloud2'
            '[gz.msgs.PointCloudPacked',
        ],
        parameters=[{
            'override_frame_id': 'camera_color_optical_frame',
        }],
        remappings=[
            ('/camera/sim_rgbd/points', '/camera/depth/color/points'),
        ],
    )

    controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'joint_state_broadcaster',
            'scaled_joint_trajectory_controller',
            'robotiq_3f_position_controller',
            '--activate-as-group',
            '--controller-manager',
            '/controller_manager',
            '--controller-manager-timeout',
            '30',
        ],
    )

    gripper_backend = Node(
        package='ur5_workcell_sim',
        executable='robotiq_3f_sim_backend.py',
        namespace='robotiq_3f',
        name='sim_backend',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    gripper_controller = Node(
        package='robotiq_3f_controller',
        executable='robotiq_3f_controller_node',
        namespace='robotiq_3f',
        name='controller',
        output='screen',
        parameters=[
            str(gripper_controller_share / 'config' / 'controller.yaml'),
            {'use_sim_time': True},
        ],
    )

    moveit = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(moveit_share / 'launch' / 'moveit.launch.py')
        ),
        condition=IfCondition(LaunchConfiguration('launch_moveit')),
        launch_arguments={
            'launch_rviz': LaunchConfiguration('launch_rviz'),
            'use_sim_time': 'true',
            'articulated_gripper': 'true',
        }.items(),
    )

    start_moveit = RegisterEventHandler(
        OnProcessExit(
            target_action=controller_spawner,
            on_exit=[
                gripper_backend,
                gripper_controller,
                moveit,
            ],
        )
    )

    return LaunchDescription([
        SetEnvironmentVariable(
            'GZ_SIM_RESOURCE_PATH',
            os.pathsep.join(resource_paths),
        ),
        DeclareLaunchArgument(
            'gazebo_gui',
            default_value='true',
            description='Launch the Gazebo graphical interface.',
        ),
        DeclareLaunchArgument(
            'launch_camera',
            default_value='true',
            description='Simulate and bridge the mounted L515 RGB-D camera.',
        ),
        DeclareLaunchArgument(
            'camera_pointcloud',
            default_value='false',
            description='Bridge the simulated registered point cloud.',
        ),
        DeclareLaunchArgument(
            'launch_moveit',
            default_value='true',
            description='Launch MoveGroup for the simulated arm.',
        ),
        DeclareLaunchArgument(
            'launch_rviz',
            default_value='true',
            description='Launch the MoveIt RViz interface.',
        ),
        robot_state_publisher,
        gazebo,
        spawn_workcell,
        clock_bridge,
        camera_bridge,
        pointcloud_bridge,
        start_moveit,
        controller_spawner,
    ])
