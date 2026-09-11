"""Tests for the safe hardware launch interface and installed defaults."""

import importlib.util
import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory

from launch import LaunchContext
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.utilities import perform_substitutions

import yaml


os.environ.setdefault('ROS_LOG_DIR', '/tmp/ur5_workcell_bringup_test_logs')


def _load_launch_description():
    package_share = Path(get_package_share_directory('ur5_workcell_bringup'))
    launch_file = package_share / 'launch' / 'hardware.launch.py'
    spec = importlib.util.spec_from_file_location(
        'workcell_hardware_launch', launch_file
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.generate_launch_description()


def _argument_defaults(launch_description):
    context = LaunchContext()
    defaults = {}
    for entity in launch_description.entities:
        if not isinstance(entity, DeclareLaunchArgument):
            continue
        defaults[entity.name] = (
            None
            if entity.default_value is None
            else perform_substitutions(context, entity.default_value)
        )
    return defaults


def test_hardware_launch_matches_config():
    """Installed launch defaults mirror the workcell configuration."""
    launch_description = _load_launch_description()
    defaults = _argument_defaults(launch_description)
    package_share = Path(get_package_share_directory('ur5_workcell_bringup'))
    with (package_share / 'config' / 'hardware.yaml').open(
            encoding='utf-8') as file:
        config = yaml.safe_load(file)
    robot = config['robot']
    peripherals = config['peripherals']
    gripper = config['gripper']
    camera = config['camera']

    expected_robot_ip = (
        None if robot['robot_ip'] in (None, '') else str(robot['robot_ip'])
    )
    assert defaults['robot_ip'] == expected_robot_ip
    assert defaults['ur_type'] == 'ur5'
    assert defaults['headless_mode'] == 'false'
    assert defaults['launch_dashboard_client'] == 'false'
    assert defaults['launch_rviz'] == str(robot['launch_rviz']).lower()
    assert defaults['launch_moveit'] == 'false'
    assert defaults['launch_moveit_rviz'] == 'true'
    assert 'activate_joint_controller' not in defaults
    assert 'moveit_allow_trajectory_execution' not in defaults
    assert defaults['launch_ft_sensor'] == 'true'
    assert defaults['launch_gripper'] == str(
        peripherals['launch_gripper']
    ).lower()
    assert defaults['launch_camera'] == str(
        peripherals['launch_camera']
    ).lower()
    assert defaults['camera_namespace'] == '/camera'
    assert defaults['camera_name'] == 'camera'
    assert defaults['camera_serial_no'] == ''
    assert defaults['camera_device_type'] == 'L515'
    assert defaults['camera_initial_reset'] == 'false'
    assert defaults['camera_color_profile'] == '640x480x30'
    assert defaults['camera_depth_profile'] == '640x480x30'
    assert defaults['camera_enable_color'] == 'true'
    assert defaults['camera_enable_depth'] == 'true'
    assert defaults['camera_align_depth'] == 'true'
    assert defaults['camera_pointcloud'] == 'false'
    assert defaults['camera_publish_tf'] == 'true'
    assert defaults['camera_base_frame_id'] == camera['base_frame_id']
    assert defaults['camera_diagnostics_period'] == '2.0'
    assert defaults['gripper_ip'] == gripper['gripper_ip']
    assert defaults['gripper_port'] == '502'
    assert defaults['gripper_unit_id'] == '0'
    assert defaults['gripper_allow_automatic_release'] == 'false'
    assert defaults['launch_gripper_joint_state_publisher'] == 'true'
    assert defaults['gripper_publish_reference_without_status'] == 'true'
    assert defaults['gripper_command_closed_position_m'] == '0.0'
    assert defaults['gripper_command_max_opening_m'] == '0.155'
    assert defaults['gripper_command_closed_raw'] == '112'
    assert defaults['gripper_command_min_effort_n'] == '15.0'
    assert defaults['gripper_command_max_effort_n'] == '60.0'
    assert defaults['gripper_command_default_effort_n'] == '30.0'
    assert defaults['gripper_command_speed'] == '20'
    assert defaults['ft_sensor_port'] == '63351'
    assert defaults['ft_frame_id'] == 'ft_measurement_frame'
    assert defaults['ft_wrench_topic'] == '/robotiq_ft_sensor/wrench'
    assert defaults['ft_startup_zero'] == 'false'
    assert defaults['ft_zero_sample_count'] == '100'
    assert defaults['use_mock_hardware'] == 'false'
    assert defaults['tf_prefix'] == ''
    assert defaults['kinematics_params_file'].endswith(
        '/ur5_workcell_description/config/ur5_calibration.yaml'
    )

    includes = [
        entity
        for entity in launch_description.entities
        if isinstance(entity, IncludeLaunchDescription)
    ]
    assert len(includes) == 6
    assert sum(include.condition is not None for include in includes) == 5


def test_hardware_config_keeps_nonautomatic_safety_invariants():
    """Verified active defaults retain the nonautomatic safety interlocks."""
    package_share = Path(get_package_share_directory('ur5_workcell_bringup'))
    config_path = package_share / 'config' / 'hardware.yaml'
    with config_path.open(encoding='utf-8') as file:
        config = yaml.safe_load(file)

    assert isinstance(config['robot']['robot_ip'], str)
    assert config['robot']['robot_ip']
    assert config['moveit']['launch'] is False
    assert config['legacy_network_reference']['robot_ip'] == '192.168.88.245'
    assert config['legacy_network_reference']['ft_tcp_port'] == 63351
    assert config['peripherals']['launch_ft_sensor'] is True
    assert config['peripherals']['launch_gripper'] is True
    assert isinstance(config['peripherals']['launch_camera'], bool)
    assert config['camera']['camera_namespace'] == '/camera'
    assert config['camera']['device_type'] == 'L515'
    assert config['camera']['color_profile'] == '640x480x30'
    assert config['camera']['depth_profile'] == '640x480x30'
    assert config['camera']['pointcloud'] is False
    assert config['camera']['base_frame_id'] == 'link'
    assert config['camera']['publish_tf'] is True
    assert config['ft_sensor']['startup_zero'] is False
    assert config['ft_sensor']['frame_id'] == 'ft_measurement_frame'
    assert isinstance(config['gripper']['gripper_ip'], str)
    assert config['gripper']['gripper_ip']
    assert config['gripper']['allow_automatic_release'] is False
    assert config['gripper']['launch_joint_state_publisher'] is True
    assert config['gripper']['publish_reference_without_status'] is True
