"""Structural checks for the Gazebo workcell simulation package."""

import importlib.util
import math
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
)
from launch.utilities import perform_substitutions
import yaml


os.environ.setdefault('ROS_LOG_DIR', '/tmp/ur5_workcell_sim_test_logs')


ARM_JOINTS = {
    'shoulder_pan_joint',
    'shoulder_lift_joint',
    'elbow_joint',
    'wrist_1_joint',
    'wrist_2_joint',
    'wrist_3_joint',
}

GRIPPER_JOINTS = {
    'robotiq_3f_finger_a_proximal_joint',
    'robotiq_3f_finger_a_middle_joint',
    'robotiq_3f_finger_a_distal_joint',
    'robotiq_3f_finger_b_scissor_joint',
    'robotiq_3f_finger_b_proximal_joint',
    'robotiq_3f_finger_b_middle_joint',
    'robotiq_3f_finger_b_distal_joint',
    'robotiq_3f_finger_c_scissor_joint',
    'robotiq_3f_finger_c_proximal_joint',
    'robotiq_3f_finger_c_middle_joint',
    'robotiq_3f_finger_c_distal_joint',
}

def _share():
    return Path(get_package_share_directory('ur5_workcell_sim'))


def _expand_sim(*arguments):
    return subprocess.run(
        [
            'xacro',
            str(_share() / 'urdf' / 'workcell_sim.urdf.xacro'),
            *arguments,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def test_sim_description_controls_the_authoritative_articulated_gripper():
    """Gazebo gets separate arm and articulated-gripper control systems."""
    root = ET.fromstring(_expand_sim())
    links = {link.attrib['name'] for link in root.findall('link')}
    assert {
        'world',
        'workcell_reference',
        'base_link',
        'tool0',
        'table',
        'camera_link',
        'camera_color_optical_frame',
    } <= links

    control = root.find("./ros2_control[@name='ur5_workcell']")
    assert control is not None
    assert control.find('hardware/plugin').text == (
        'gz_ros2_control/GazeboSimSystem'
    )
    controlled_joints = {
        joint.attrib['name'] for joint in control.findall('joint')
    }
    assert controlled_joints == ARM_JOINTS
    shoulder_pan = control.find("./joint[@name='shoulder_pan_joint']")
    shoulder_pan_initial = shoulder_pan.find(
        "./state_interface[@name='position']/param[@name='initial_value']"
    )
    assert math.isclose(float(shoulder_pan_initial.text), 0.0)

    base_joint = root.find("./joint[@name='base_joint']")
    base_rpy = tuple(map(
        float, base_joint.find('origin').attrib['rpy'].split()
    ))
    assert base_rpy == (0.0, 0.0, math.pi)

    gripper_control = root.find("./ros2_control[@name='robotiq_3f_sim']")
    assert gripper_control is not None
    assert gripper_control.find('hardware/plugin').text == (
        'gz_ros2_control/GazeboSimSystem'
    )
    assert {
        joint.attrib['name'] for joint in gripper_control.findall('joint')
    } == GRIPPER_JOINTS

    movable_gripper_joints = {
        joint.attrib['name']
        for joint in root.findall('joint')
        if joint.attrib['type'] != 'fixed'
        and joint.attrib['name'].startswith('robotiq_3f_')
    }
    assert movable_gripper_joints == GRIPPER_JOINTS

    control_plugin = root.find(
        ".//plugin[@name='gz_ros2_control::GazeboSimROS2ControlPlugin']"
    )
    assert control_plugin is not None
    assert control_plugin.find('hold_joints').text == 'true'
    assert control_plugin.find('position_proportional_gain').text == '0.5'

def test_l515_rgbd_sensor_matches_the_active_camera_interface():
    """The simulated RGB-D sensor keeps the real camera topic contract."""
    root = ET.fromstring(_expand_sim())
    optical_joint = root.find("./joint[@name='camera_color_optical_joint']")
    assert optical_joint is not None
    assert optical_joint.find('parent').attrib['link'] == 'camera_link'
    optical_origin = optical_joint.find('origin')
    assert optical_origin.attrib['xyz'].split() == [
        '0.0045189945958554745',
        '0.00022442915360443294',
        '0.014033393003046513',
    ]

    gazebo = root.find("./gazebo[@reference='camera_link']")
    sensor = gazebo.find("./sensor[@name='l515_rgbd']")
    assert sensor.attrib['type'] == 'rgbd_camera'
    assert sensor.find('update_rate').text == '30'
    assert sensor.find('topic').text == '/camera/sim_rgbd'
    camera = sensor.find('camera')
    assert camera.find('image/width').text == '640'
    assert camera.find('image/height').text == '480'
    assert camera.find('clip/near').text == '0.01'
    assert camera.find('depth_camera/clip/near').text == '0.25'
    assert camera.find('optical_frame_id').text == (
        'camera_color_optical_frame'
    )

    disabled_root = ET.fromstring(_expand_sim('simulate_camera:=false'))
    disabled_links = {
        link.attrib['name'] for link in disabled_root.findall('link')
    }
    assert 'camera_link' in disabled_links
    assert 'camera_color_optical_frame' not in disabled_links
    assert disabled_root.find(".//sensor[@name='l515_rgbd']") is None


def test_controller_and_launch_contracts():
    """Controller names match MoveIt and simulation defaults are usable."""
    with (_share() / 'config' / 'ur_controllers.yaml').open(
        encoding='utf-8'
    ) as config_file:
        config = yaml.safe_load(config_file)
    assert set(config['scaled_joint_trajectory_controller'][
        'ros__parameters']['joints']) == ARM_JOINTS
    assert set(config['robotiq_3f_position_controller'][
        'ros__parameters']['joints']) == GRIPPER_JOINTS
    assert config['controller_manager']['ros__parameters'][
        'robotiq_3f_position_controller']['type'] == (
            'position_controllers/JointGroupPositionController'
        )

    with (_share() / 'config' / 'camera_bridge.yaml').open(
        encoding='utf-8'
    ) as config_file:
        camera_bridges = yaml.safe_load(config_file)
    bridge_topics = {
        entry['ros_topic_name']: entry for entry in camera_bridges
    }
    assert set(bridge_topics) == {
        '/camera/color/image_raw',
        '/camera/aligned_depth_to_color/image_raw',
        '/camera/depth/image_rect_raw',
        '/camera/color/camera_info',
        '/camera/aligned_depth_to_color/camera_info',
        '/camera/depth/camera_info',
    }
    assert all(
        entry['direction'] == 'GZ_TO_ROS'
        and entry['frame_id'] == 'camera_color_optical_frame'
        for entry in camera_bridges
    )

    world = ET.parse(_share() / 'worlds' / 'workcell.sdf').getroot()
    sensors_plugin = world.find(
        ".//plugin[@name='gz::sim::systems::Sensors']"
    )
    assert sensors_plugin is not None
    assert sensors_plugin.find('render_engine').text == 'ogre2'

    launch_path = _share() / 'launch' / 'sim.launch.py'
    spec = importlib.util.spec_from_file_location('workcell_sim', launch_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    description = module.generate_launch_description()
    context = LaunchContext()
    defaults = {
        entity.name: perform_substitutions(context, entity.default_value)
        for entity in description.entities
        if isinstance(entity, DeclareLaunchArgument)
    }
    assert defaults == {
        'gazebo_gui': 'true',
        'launch_camera': 'true',
        'camera_pointcloud': 'false',
        'launch_moveit': 'true',
        'launch_rviz': 'true',
    }
    context.launch_configurations.update(defaults)

    includes = [
        entity for entity in description.entities
        if isinstance(entity, IncludeLaunchDescription)
    ]
    for entity in description.entities:
        event_handler = getattr(entity, 'event_handler', None)
        if event_handler is None:
            continue
        for value in vars(event_handler).values():
            if isinstance(value, list):
                includes.extend(
                    action for action in value
                    if isinstance(action, IncludeLaunchDescription)
                )
    assert len(includes) == 2
    gazebo_arguments = dict(includes[0].launch_arguments)
    gazebo_args = perform_substitutions(
        context,
        [gazebo_arguments['gz_args']],
    )
    assert 'gz-physics-bullet-featherstone-plugin' in gazebo_args
    assert 'workcell.sdf' in gazebo_args
    assert '-r' in gazebo_args.split()

    environment = next(
        entity for entity in description.entities
        if isinstance(entity, SetEnvironmentVariable)
    )
    assert perform_substitutions(context, environment.name) == (
        'GZ_SIM_RESOURCE_PATH'
    )
    resource_path = perform_substitutions(context, environment.value)
    assert 'robotiq_3f_description' in resource_path
    assert 'realsense_l515_description' in resource_path

    moveit_arguments = dict(includes[1].launch_arguments)
    assert moveit_arguments['use_sim_time'] == 'true'
    assert moveit_arguments['articulated_gripper'] == 'true'
