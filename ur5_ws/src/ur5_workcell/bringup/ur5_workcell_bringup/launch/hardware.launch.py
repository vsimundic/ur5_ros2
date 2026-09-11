"""Launch the authoritative UR5 workcell through the official UR driver."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

import yaml


JOINT_CONTROLLERS = [
    'scaled_joint_trajectory_controller',
    'joint_trajectory_controller',
    'forward_velocity_controller',
    'forward_position_controller',
    'freedrive_mode_controller',
    'passthrough_trajectory_controller',
]


def _launch_text(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


def _argument(name, default, description, choices=None, required=False):
    options = {'description': description}
    if not required or default not in (None, ''):
        options['default_value'] = _launch_text(default)
    if choices is not None:
        options['choices'] = choices
    return DeclareLaunchArgument(name, **options)


def generate_launch_description():
    """Build a safe-by-default UR5 hardware launch description."""
    bringup_share = Path(get_package_share_directory('ur5_workcell_bringup'))
    description_share = Path(
        get_package_share_directory('ur5_workcell_description')
    )
    driver_share = Path(get_package_share_directory('ur_robot_driver'))
    ft_streamer_share = Path(
        get_package_share_directory('robotiq_ft_streamer')
    )
    gripper_controller_share = Path(
        get_package_share_directory('robotiq_3f_controller')
    )
    gripper_state_publisher_share = Path(
        get_package_share_directory('robotiq_3f_state_publisher')
    )
    realsense_share = Path(get_package_share_directory('realsense2_camera'))
    moveit_share = Path(
        get_package_share_directory('ur5_workcell_moveit_config')
    )

    hardware_config = bringup_share / 'config' / 'hardware.yaml'
    with hardware_config.open(encoding='utf-8') as config_file:
        defaults = yaml.safe_load(config_file)
    robot_defaults = defaults['robot']
    peripheral_defaults = defaults['peripherals']
    ft_defaults = defaults['ft_sensor']
    gripper_defaults = defaults['gripper']
    camera_defaults = defaults['camera']
    moveit_defaults = defaults['moveit']

    arguments = [
        _argument(
            'robot_ip',
            robot_defaults['robot_ip'],
            'IP address of the UR controller. Required while hardware.yaml '
            'leaves it unset.',
            required=True,
        ),
        _argument(
            'ur_type',
            robot_defaults['ur_type'],
            'Universal Robots model.',
            choices=['ur5'],
        ),
        _argument(
            'kinematics_params_file',
            description_share / 'config' / 'ur5_calibration.yaml',
            'Absolute path to the calibration YAML for this physical UR5.',
        ),
        _argument(
            'reverse_ip',
            robot_defaults['reverse_ip'],
            'Local IP used for UR reverse connections.',
        ),
        _argument(
            'tf_prefix',
            robot_defaults['tf_prefix'],
            'Prefix applied to UR links and joints.',
        ),
        _argument(
            'safety_limits',
            robot_defaults['safety_limits'],
            'Enable URDF safety limits.',
        ),
        _argument(
            'safety_pos_margin',
            robot_defaults['safety_pos_margin'],
            'Safety-limit position margin.',
        ),
        _argument(
            'safety_k_position',
            robot_defaults['safety_k_position'],
            'Safety-limit position gain.',
        ),
        _argument(
            'use_mock_hardware',
            robot_defaults['use_mock_hardware'],
            'Use ros2_control mock hardware instead of connecting to the UR5.',
        ),
        _argument(
            'mock_sensor_commands',
            robot_defaults['mock_sensor_commands'],
            'Expose mock sensor command interfaces when mock hardware is '
            'enabled.',
        ),
        _argument(
            'headless_mode',
            robot_defaults['headless_mode'],
            'Allow the driver to send the external-control script directly.',
        ),
        _argument(
            'initial_joint_controller',
            robot_defaults['initial_joint_controller'],
            'Joint controller to load.',
            choices=JOINT_CONTROLLERS,
        ),
        _argument(
            'launch_dashboard_client',
            robot_defaults['launch_dashboard_client'],
            'Launch the UR dashboard client.',
        ),
        _argument(
            'launch_rviz',
            robot_defaults['launch_rviz'],
            'Launch RViz with the workcell configuration.',
        ),
        _argument(
            'launch_moveit',
            moveit_defaults['launch'],
            'Launch MoveIt after starting the workcell. Defaults to false.',
        ),
        _argument(
            'launch_moveit_rviz',
            moveit_defaults['launch_rviz'],
            'Launch the MoveIt RViz interface.',
        ),
        _argument(
            'controller_spawner_timeout',
            robot_defaults['controller_spawner_timeout'],
            'Controller-manager spawner timeout in seconds.',
        ),
        _argument(
            'launch_ft_sensor',
            peripheral_defaults['launch_ft_sensor'],
            'Launch the external Robotiq FT TCP streamer.',
        ),
        _argument(
            'ft_sensor_port',
            ft_defaults['sensor_port'],
            'Robotiq FT TCP stream port on the UR controller.',
        ),
        _argument(
            'ft_frame_id',
            ft_defaults['frame_id'],
            'Frame assigned to external FT wrench messages.',
        ),
        _argument(
            'ft_wrench_topic',
            ft_defaults['wrench_topic'],
            'External Robotiq WrenchStamped topic.',
        ),
        _argument(
            'ft_publish_rate_hz',
            ft_defaults['publish_rate_hz'],
            'Maximum external FT publication rate.',
        ),
        _argument(
            'ft_startup_zero',
            ft_defaults['startup_zero'],
            'Software-zero the external FT stream at startup.',
        ),
        _argument(
            'ft_zero_sample_count',
            ft_defaults['zero_sample_count'],
            'Samples averaged for external FT software zeroing.',
        ),
        _argument(
            'launch_gripper',
            peripheral_defaults['launch_gripper'],
            'Launch the Robotiq 3F status/controller stack. Defaults to false.',
        ),
        _argument(
            'gripper_ip',
            gripper_defaults['gripper_ip'],
            'IP address of the Robotiq 3F Modbus TCP device.',
        ),
        _argument(
            'gripper_port',
            gripper_defaults['port'],
            'Robotiq 3F Modbus TCP port.',
        ),
        _argument(
            'gripper_unit_id',
            gripper_defaults['unit_id'],
            'Robotiq 3F Modbus unit identifier.',
        ),
        _argument(
            'gripper_poll_rate_hz',
            gripper_defaults['poll_rate_hz'],
            'Robotiq 3F status polling rate.',
        ),
        _argument(
            'gripper_allow_automatic_release',
            gripper_defaults['allow_automatic_release'],
            'Permit dangerous Robotiq automatic-release commands.',
        ),
        _argument(
            'launch_gripper_joint_state_publisher',
            gripper_defaults['launch_joint_state_publisher'],
            'Publish the articulated 3F reference/status pose.',
        ),
        _argument(
            'gripper_publish_reference_without_status',
            gripper_defaults['publish_reference_without_status'],
            'Publish the reviewed Basic/open reference before valid gripper status.',
        ),
        _argument(
            'gripper_command_closed_position_m',
            gripper_defaults['gripper_command_closed_position_m'],
            'Closed gap used by the standard GripperCommand adapter.',
        ),
        _argument(
            'gripper_command_max_opening_m',
            gripper_defaults['gripper_command_max_opening_m'],
            'Open gap used by the standard GripperCommand adapter.',
        ),
        _argument(
            'gripper_command_closed_raw',
            gripper_defaults['gripper_command_closed_raw'],
            'Pinch raw position that represents fully closed.',
        ),
        _argument(
            'gripper_command_min_effort_n',
            gripper_defaults['gripper_command_min_effort_n'],
            'Minimum per-finger effort supported by the adapter.',
        ),
        _argument(
            'gripper_command_max_effort_n',
            gripper_defaults['gripper_command_max_effort_n'],
            'Maximum per-finger effort supported by the adapter.',
        ),
        _argument(
            'gripper_command_default_effort_n',
            gripper_defaults['gripper_command_default_effort_n'],
            'Effort used when a standard goal requests zero.',
        ),
        _argument(
            'gripper_command_speed',
            gripper_defaults['gripper_command_speed'],
            'Native 0..255 speed used by standard GripperCommand goals.',
        ),
        _argument(
            'launch_camera',
            peripheral_defaults['launch_camera'],
            'Launch the wrist-mounted RealSense L515. Defaults to false.',
        ),
        _argument(
            'camera_namespace',
            camera_defaults['camera_namespace'],
            'ROS namespace for RealSense streams; /camera preserves /camera/* topics.',
        ),
        _argument(
            'camera_name',
            camera_defaults['camera_name'],
            'RealSense camera name used to construct frame IDs.',
        ),
        _argument(
            'camera_serial_no',
            camera_defaults['serial_no'],
            'Optional RealSense serial number; empty selects the first L515.',
        ),
        _argument(
            'camera_device_type',
            camera_defaults['device_type'],
            'RealSense device type filter.',
        ),
        _argument(
            'camera_initial_reset',
            camera_defaults['initial_reset'],
            'Reset the RealSense device once during startup.',
        ),
        _argument(
            'camera_color_profile',
            camera_defaults['color_profile'],
            'RealSense color stream profile WIDTHxHEIGHTxFPS.',
        ),
        _argument(
            'camera_depth_profile',
            camera_defaults['depth_profile'],
            'RealSense depth stream profile WIDTHxHEIGHTxFPS; L515 default is 640x480x30.',
        ),
        _argument(
            'camera_enable_color',
            camera_defaults['enable_color'],
            'Enable the RealSense color stream.',
        ),
        _argument(
            'camera_enable_depth',
            camera_defaults['enable_depth'],
            'Enable the RealSense depth stream.',
        ),
        _argument(
            'camera_align_depth',
            camera_defaults['align_depth'],
            'Publish depth aligned to the color stream.',
        ),
        _argument(
            'camera_pointcloud',
            camera_defaults['pointcloud'],
            'Publish the RealSense point cloud.',
        ),
        _argument(
            'camera_publish_tf',
            camera_defaults['publish_tf'],
            'Publish downstream RealSense sensor and optical transforms.',
        ),
        _argument(
            'camera_base_frame_id',
            camera_defaults['base_frame_id'],
            'Base-frame suffix; camera_name=\"camera\" and \"link\" form camera_link.',
        ),
        _argument(
            'camera_diagnostics_period',
            camera_defaults['diagnostics_period'],
            'RealSense diagnostics publication period in seconds.',
        ),
    ]

    configurations = {
        name: LaunchConfiguration(name)
        for name in [
            'robot_ip',
            'ur_type',
            'kinematics_params_file',
            'reverse_ip',
            'tf_prefix',
            'safety_limits',
            'safety_pos_margin',
            'safety_k_position',
            'use_mock_hardware',
            'mock_sensor_commands',
            'headless_mode',
            'initial_joint_controller',
            'launch_dashboard_client',
            'launch_rviz',
            'controller_spawner_timeout',
        ]
    }

    driver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(driver_share / 'launch' / 'ur_control.launch.py')
        ),
        launch_arguments={
            **configurations,
            'description_file': str(
                description_share / 'urdf' / 'workcell_control.urdf.xacro'
            ),
            'rviz_config_file': str(
                description_share / 'rviz' / 'view_workcell.rviz'
            ),
            'use_tool_communication': 'false',
        }.items(),
    )

    ft_streamer = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(ft_streamer_share / 'launch' / 'ft_streamer.launch.py')
        ),
        condition=IfCondition(LaunchConfiguration('launch_ft_sensor')),
        launch_arguments={
            'robot_ip': LaunchConfiguration('robot_ip'),
            'sensor_port': LaunchConfiguration('ft_sensor_port'),
            'frame_id': LaunchConfiguration('ft_frame_id'),
            'wrench_topic': LaunchConfiguration('ft_wrench_topic'),
            'publish_rate_hz': LaunchConfiguration('ft_publish_rate_hz'),
            'startup_zero': LaunchConfiguration('ft_startup_zero'),
            'zero_sample_count': LaunchConfiguration(
                'ft_zero_sample_count'
            ),
        }.items(),
    )

    gripper = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(gripper_controller_share / 'launch' / 'hardware.launch.py')
        ),
        condition=IfCondition(LaunchConfiguration('launch_gripper')),
        launch_arguments={
            'gripper_ip': LaunchConfiguration('gripper_ip'),
            'port': LaunchConfiguration('gripper_port'),
            'unit_id': LaunchConfiguration('gripper_unit_id'),
            'poll_rate_hz': LaunchConfiguration('gripper_poll_rate_hz'),
            'allow_automatic_release': LaunchConfiguration(
                'gripper_allow_automatic_release'
            ),
            'gripper_command_closed_position_m': LaunchConfiguration(
                'gripper_command_closed_position_m'
            ),
            'gripper_command_max_opening_m': LaunchConfiguration(
                'gripper_command_max_opening_m'
            ),
            'gripper_command_closed_raw': LaunchConfiguration(
                'gripper_command_closed_raw'
            ),
            'gripper_command_min_effort_n': LaunchConfiguration(
                'gripper_command_min_effort_n'
            ),
            'gripper_command_max_effort_n': LaunchConfiguration(
                'gripper_command_max_effort_n'
            ),
            'gripper_command_default_effort_n': LaunchConfiguration(
                'gripper_command_default_effort_n'
            ),
            'gripper_command_speed': LaunchConfiguration(
                'gripper_command_speed'
            ),
            'launch_joint_state_publisher': 'false',
            'tf_prefix': LaunchConfiguration('tf_prefix'),
        }.items(),
    )

    gripper_joint_states = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(
                gripper_state_publisher_share
                / 'launch'
                / 'joint_states.launch.py'
            )
        ),
        condition=IfCondition(
            LaunchConfiguration('launch_gripper_joint_state_publisher')
        ),
        launch_arguments={
            'tf_prefix': LaunchConfiguration('tf_prefix'),
            'publish_reference_without_status': LaunchConfiguration(
                'gripper_publish_reference_without_status'
            ),
        }.items(),
    )

    camera = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(realsense_share / 'launch' / 'rs_launch.py')
        ),
        condition=IfCondition(LaunchConfiguration('launch_camera')),
        launch_arguments={
            'camera_namespace': LaunchConfiguration('camera_namespace'),
            'camera_name': LaunchConfiguration('camera_name'),
            'serial_no': LaunchConfiguration('camera_serial_no'),
            'device_type': LaunchConfiguration('camera_device_type'),
            'initial_reset': LaunchConfiguration('camera_initial_reset'),
            'enable_color': LaunchConfiguration('camera_enable_color'),
            'rgb_camera.profile': LaunchConfiguration(
                'camera_color_profile'
            ),
            'enable_depth': LaunchConfiguration('camera_enable_depth'),
            'depth_module.profile': LaunchConfiguration(
                'camera_depth_profile'
            ),
            'align_depth.enable': LaunchConfiguration('camera_align_depth'),
            'pointcloud.enable': LaunchConfiguration('camera_pointcloud'),
            'publish_tf': LaunchConfiguration('camera_publish_tf'),
            'base_frame_id': LaunchConfiguration('camera_base_frame_id'),
            'tf_prefix': LaunchConfiguration('tf_prefix'),
            'diagnostics_period': LaunchConfiguration(
                'camera_diagnostics_period'
            ),
        }.items(),
    )

    moveit = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(moveit_share / 'launch' / 'moveit.launch.py')
        ),
        condition=IfCondition(LaunchConfiguration('launch_moveit')),
        launch_arguments={
            'launch_rviz': LaunchConfiguration('launch_moveit_rviz'),
        }.items(),
    )

    return LaunchDescription(
        arguments
        + [
            driver,
            ft_streamer,
            gripper,
            gripper_joint_states,
            camera,
            moveit,
        ]
    )
