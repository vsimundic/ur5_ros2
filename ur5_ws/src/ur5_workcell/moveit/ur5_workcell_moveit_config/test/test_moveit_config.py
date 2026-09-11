"""Structural checks for the authoritative workcell MoveIt configuration."""

import importlib.util
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext
from launch.actions import DeclareLaunchArgument
from launch.utilities import perform_substitutions
import yaml


os.environ.setdefault('ROS_LOG_DIR', '/tmp/ur5_workcell_moveit_test_logs')


ARM_JOINTS = {
    'shoulder_pan_joint',
    'shoulder_lift_joint',
    'elbow_joint',
    'wrist_1_joint',
    'wrist_2_joint',
    'wrist_3_joint',
}


def _share(package):
    return Path(get_package_share_directory(package))


def test_semantic_model_uses_tool0_and_only_six_arm_joints():
    srdf = ET.parse(_share('ur5_workcell_moveit_config') / 'config' /
                    'ur5_workcell.srdf').getroot()
    group = srdf.find("./group[@name='ur_manipulator']")
    chain = group.find('chain')
    assert chain.attrib == {'base_link': 'base_link', 'tip_link': 'tool0'}

    xacro = (
        _share('ur5_workcell_description')
        / 'urdf'
        / 'workcell.urdf.xacro'
    )
    result = subprocess.run(
        ['xacro', str(xacro)], check=True, capture_output=True, text=True
    )
    urdf = ET.fromstring(result.stdout)
    movable = {
        joint.attrib['name']
        for joint in urdf.findall('joint')
        if joint.attrib['type'] != 'fixed'
    }
    assert ARM_JOINTS <= movable
    assert any(name.startswith('robotiq_3f_') for name in movable)
    assert srdf.find("./group[@name='gripper']") is None

    links = {link.attrib['name'] for link in urdf.findall('link')}
    disabled_pairs = [
        tuple(sorted((entry.attrib['link1'], entry.attrib['link2'])))
        for entry in srdf.findall('disable_collisions')
    ]
    assert len(disabled_pairs) == 237
    assert len(disabled_pairs) == len(set(disabled_pairs))
    assert all(set(pair) <= links for pair in disabled_pairs)


def test_controller_mapping_matches_official_ur_arm_interface():
    with (_share('ur5_workcell_moveit_config') / 'config' /
          'moveit_controllers.yaml').open(encoding='utf-8') as file:
        config = yaml.safe_load(file)
    manager = config['moveit_simple_controller_manager']
    scaled = manager['scaled_joint_trajectory_controller']
    assert scaled['action_ns'] == 'follow_joint_trajectory'
    assert scaled['type'] == 'FollowJointTrajectory'
    assert scaled['default'] is True
    assert set(scaled['joints']) == ARM_JOINTS


def test_rrtstar_is_the_default_arm_planner():
    with (_share('ur5_workcell_moveit_config') / 'config' /
          'ompl_planning.yaml').open(encoding='utf-8') as file:
        config = yaml.safe_load(file)

    planners = config['planner_configs']
    assert planners['RRTstarkConfigDefault']['type'] == 'geometric::RRTstar'
    assert planners['RRTConnectkConfigDefault']['type'] == (
        'geometric::RRTConnect'
    )

    arm = config['ur_manipulator']
    assert arm['default_planner_config'] == 'RRTstarkConfigDefault'
    assert set(arm['planner_configs']) == set(planners)


def test_launch_defaults_match_hardware_description():
    launch_path = (
        _share('ur5_workcell_moveit_config')
        / 'launch'
        / 'moveit.launch.py'
    )
    spec = importlib.util.spec_from_file_location('moveit_launch', launch_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    description = module.generate_launch_description()
    context = LaunchContext()
    defaults = {
        entity.name: perform_substitutions(context, entity.default_value)
        for entity in description.entities
        if isinstance(entity, DeclareLaunchArgument)
    }
    assert defaults['launch_rviz'] == 'true'
    assert defaults['use_sim_time'] == 'false'
    assert defaults['articulated_gripper'] == 'true'
