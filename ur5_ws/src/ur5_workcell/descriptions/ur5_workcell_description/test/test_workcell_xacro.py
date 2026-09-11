"""Structural tests for the authoritative view and control descriptions."""

import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory

import yaml


def _expand(*mappings, xacro_name='workcell.urdf.xacro'):
    package_share = Path(
        get_package_share_directory('ur5_workcell_description')
    )
    xacro_file = package_share / 'urdf' / xacro_name
    command = [shutil.which('xacro'), str(xacro_file), *mappings]
    result = subprocess.run(
        command, check=True, capture_output=True, text=True
    )
    return result.stdout


def _calibration():
    package_share = Path(
        get_package_share_directory('ur5_workcell_description')
    )
    with (package_share / 'config' / 'ur5_calibration.yaml').open(
        encoding='utf-8'
    ) as calibration_file:
        return yaml.safe_load(calibration_file)['kinematics']


def _camera_extrinsics():
    package_share = Path(
        get_package_share_directory('ur5_workcell_description')
    )
    with (package_share / 'config' / 'camera_extrinsics.yaml').open(
        encoding='utf-8'
    ) as calibration_file:
        return yaml.safe_load(calibration_file)['camera_extrinsics']


def _origin(root, joint_name):
    joint = root.find(f"./joint[@name='{joint_name}']")
    assert joint is not None
    origin = joint.find('origin')
    assert origin is not None
    xyz = tuple(float(value) for value in origin.attrib['xyz'].split())
    rpy = tuple(float(value) for value in origin.attrib['rpy'].split())
    return xyz, rpy


def _assert_vector(actual, expected):
    assert len(actual) == len(expected)
    for actual_value, expected_value in zip(actual, expected):
        assert math.isclose(actual_value, expected_value, abs_tol=1e-12)


def test_default_workcell_expands_and_preserves_reviewed_transforms():
    """The view model expands and preserves the reviewed physical chain."""
    urdf = _expand()
    root = ET.fromstring(urdf)
    links = {element.attrib['name'] for element in root.findall('link')}

    required_links = {
        'world',
        'workcell_reference',
        'table',
        'base_link',
        'tool0',
        'ft300_mounting_plate',
        'ft300_sensor',
        'ft_measurement_frame',
        'gripper_coupler',
        'robotiq_3f_frame',
        'AGS_palm',
        'gripper_power_plug',
        'gripper_ethernet_plug',
        'camera_link',
        'tactile_sensor',
        'grasp_tcp',
    }
    assert required_links <= links
    assert 'wall' not in links
    assert root.find('gazebo') is None
    assert root.find('ros2_control') is None

    migrated_transforms = {
        'ft300_mount_joint': ((0, 0, 0.0067), (0, 0, 0)),
        'ft_sensor_to_gripper_coupler_joint': (
            (0, 0, -0.0085),
            (math.pi, 0, 0),
        ),
        'robotiq_3f_mount_joint': (
            (0, 0, 0.0127),
            (math.pi / 2, 0, -math.pi / 4),
        ),
        'tactile_sensor_joint': (
            (0, -0.01117, 0.02588),
            (math.pi / 2, 0, 0),
        ),
    }
    for joint_name, expected_origin in migrated_transforms.items():
        expected_xyz, expected_rpy = expected_origin
        xyz, rpy = _origin(root, joint_name)
        _assert_vector(xyz, expected_xyz)
        _assert_vector(rpy, expected_rpy)

    camera_extrinsics = _camera_extrinsics()
    assert camera_extrinsics['calibrated_parent_frame'] == 'tool0'
    assert (
        camera_extrinsics['calibrated_child_frame']
        == 'camera_color_optical_frame'
    )
    camera_mount = camera_extrinsics['derived_tool0_to_camera_link']
    camera_xyz, camera_rpy = _origin(root, 'camera_mount_joint')
    _assert_vector(camera_xyz, camera_mount['xyz'])
    _assert_vector(camera_rpy, camera_mount['rpy'])

    camera = root.find("./link[@name='camera_link']")
    for kind, expected_xyz in (
        ('visual', (0.0045, 0, 0.009)),
        ('collision', (-0.006456, 0, 0.009)),
        ('inertial', (-0.006456, 0, 0.009)),
    ):
        origin = camera.find(f'{kind}/origin')
        _assert_vector(
            tuple(map(float, origin.attrib['xyz'].split())), expected_xyz,
        )
        _assert_vector(
            tuple(map(float, origin.attrib['rpy'].split())),
            (math.pi / 2, 0, math.pi / 2),
        )

    scale = camera_extrinsics['rotation_scale']
    raw = camera_extrinsics['raw_similarity_matrix']
    normalized = camera_extrinsics[
        'normalized_tool0_to_color_optical_matrix'
    ]
    for row in range(3):
        for column in range(3):
            assert math.isclose(
                raw[row][column] / scale,
                normalized[row][column],
                abs_tol=1e-12,
            )

    tactile_joint = root.find("./joint[@name='tactile_sensor_joint']")
    assert tactile_joint.find('parent').attrib['link'] == 'AGS_finger-dist002'

    table_joint = root.find("./joint[@name='table_joint']")
    assert table_joint.find('parent').attrib['link'] == 'workcell_reference'
    _, base_rpy = _origin(root, 'base_joint')
    _assert_vector(base_rpy, (0, 0, math.pi))
    table = root.find("./link[@name='table']")
    for kind in ('visual', 'collision'):
        origin = table.find(f'{kind}/origin')
        _assert_vector(
            tuple(map(float, origin.attrib['xyz'].split())),
            (0, -0.54, -0.45),
        )
        size = table.find(f'{kind}/geometry/box').attrib['size']
        _assert_vector(tuple(map(float, size.split())), (0.9, 1.5, 0.9))

    shoulder_xyz, _ = _origin(root, 'shoulder_pan_joint')
    assert math.isclose(
        shoulder_xyz[2],
        float(_calibration()['shoulder']['z']),
        abs_tol=1e-12,
    )

    with tempfile.NamedTemporaryFile(mode='w', suffix='.urdf') as urdf_file:
        urdf_file.write(urdf)
        urdf_file.flush()
        subprocess.run(
            [shutil.which('check_urdf'), urdf_file.name],
            check=True,
            capture_output=True,
            text=True,
        )


def test_prefix_and_optional_components():
    """Prefixes propagate and optional component geometry can be disabled."""
    root = ET.fromstring(_expand(
        'tf_prefix:=test_',
        'include_camera:=false',
        'include_tactile_sensor:=false',
        'include_cable_plugs:=false',
        'include_table:=false',
    ))
    links = {element.attrib['name'] for element in root.findall('link')}

    assert 'world' in links
    assert 'test_workcell_reference' in links
    assert 'test_base_link' in links
    assert 'test_tool0' in links
    assert 'test_ft_measurement_frame' in links
    assert 'test_AGS_palm' in links
    assert 'test_grasp_tcp' in links
    assert 'test_camera_link' not in links
    assert 'test_tactile_sensor' not in links
    assert 'test_gripper_power_plug' not in links
    assert 'table' not in links


def test_table_dimensions_and_edge_offset_are_configurable():
    """The fixed environment preserves the base-relative placement rule."""
    root = ET.fromstring(_expand(
        'table_width:=1.0',
        'table_length:=2.0',
        'table_height:=0.8',
        'table_robot_edge_offset:=0.3',
    ))
    table = root.find("./link[@name='table']")
    collision = table.find('collision')
    _assert_vector(
        tuple(map(float, collision.find('origin').attrib['xyz'].split())),
        (0, -0.7, -0.4),
    )
    _assert_vector(
        tuple(map(float, collision.find('geometry/box').attrib['size'].split())),
        (1.0, 2.0, 0.8),
    )


def test_tactile_sensor_prefixes_finger_a_distal_attachment():
    """The tactile body follows the prefixed articulated Finger A tip."""
    root = ET.fromstring(_expand('tf_prefix:=cell_'))
    joint = root.find("./joint[@name='cell_tactile_sensor_joint']")
    assert joint is not None
    assert joint.find('parent').attrib['link'] == 'cell_AGS_finger-dist002'
    assert joint.find('child').attrib['link'] == 'cell_tactile_sensor'


def test_articulated_gripper_preserves_fixed_reference_pose():
    """The movable AGS model decomposes each reviewed fixed transform at q=0."""
    articulated = ET.fromstring(_expand())
    fixed = ET.fromstring(_expand('articulated_gripper:=false'))

    articulated_joints = {
        joint.attrib['name']: joint for joint in articulated.findall('joint')
    }
    fixed_joints = {
        joint.attrib['name']: joint for joint in fixed.findall('joint')
    }
    gripper_movable = {
        name for name, joint in articulated_joints.items()
        if name.startswith('robotiq_3f_') and joint.attrib['type'] == 'revolute'
    }
    assert len(gripper_movable) == 11

    expected = {
        'robotiq_3f_finger_b_scissor_joint':
            'AGS_palm_to_AGS_finger-base_joint',
        'robotiq_3f_finger_b_proximal_joint':
            'AGS_finger-base_to_AGS_finger-prox_joint',
        'robotiq_3f_finger_b_middle_joint':
            'AGS_finger-prox_to_AGS_finger-med_joint',
        'robotiq_3f_finger_b_distal_joint':
            'AGS_finger-med_to_AGS_finger-dist_joint',
        'robotiq_3f_finger_c_scissor_joint':
            'AGS_palm_to_AGS_finger-base001_joint',
        'robotiq_3f_finger_c_proximal_joint':
            'AGS_finger-base001_to_AGS_finger-prox001_joint',
        'robotiq_3f_finger_c_middle_joint':
            'AGS_finger-prox001_to_AGS_finger-med001_joint',
        'robotiq_3f_finger_c_distal_joint':
            'AGS_finger-med001_to_AGS_finger-dist001_joint',
        'robotiq_3f_finger_a_proximal_joint':
            'AGS_finger-base002_to_AGS_finger-prox002_joint',
        'robotiq_3f_finger_a_middle_joint':
            'AGS_finger-prox002_to_AGS_finger-med002_joint',
        'robotiq_3f_finger_a_distal_joint':
            'AGS_finger-med002_to_AGS_finger-dist002_joint',
    }
    for moving_name, old_fixed_name in expected.items():
        moving_origin = articulated_joints[moving_name].find('origin')
        mesh_origin = articulated_joints[
            f'{moving_name}_mesh_joint'
        ].find('origin')
        old_origin = fixed_joints[old_fixed_name].find('origin')
        moving_xyz = tuple(
            float(value) for value in moving_origin.attrib['xyz'].split()
        )
        mesh_xyz = tuple(
            float(value) for value in mesh_origin.attrib['xyz'].split()
        )
        old_xyz = tuple(
            float(value) for value in old_origin.attrib['xyz'].split()
        )
        _assert_vector(
            tuple(a + b for a, b in zip(moving_xyz, mesh_xyz)),
            old_xyz,
        )
        assert moving_origin.attrib['rpy'] == '0 0 0'
        assert mesh_origin.attrib['rpy'] == old_origin.attrib['rpy']

    assert fixed_joints[
        'AGS_palm_to_AGS_finger-base002_joint'
    ].attrib['type'] == 'fixed'


def test_articulated_gripper_uses_fitted_middle_pivots():
    """Normal articulation promotes the three accepted CSV pivot centers."""
    root = ET.fromstring(_expand())
    expected = {
        'robotiq_3f_finger_a_middle_joint':
            (-0.058187455, -0.001425852, 0.00805),
        'robotiq_3f_finger_b_middle_joint':
            (-0.058189366, -0.0013289835, 0.00804),
        'robotiq_3f_finger_c_middle_joint':
            (-0.058953474, -0.0012468926, 0.00805),
    }
    for joint_name, expected_xyz in expected.items():
        xyz, _ = _origin(root, joint_name)
        _assert_vector(xyz, expected_xyz)
        mesh_xyz, _ = _origin(root, f'{joint_name}_mesh_joint')
        _assert_vector(mesh_xyz, (-0.01162, 0.0, 0.0))


def test_articulated_gripper_prefixes_moving_joints():
    """The status mapper can use the same prefix as the workcell description."""
    root = ET.fromstring(_expand('tf_prefix:=cell_'))
    movable = {
        joint.attrib['name'] for joint in root.findall('joint')
        if joint.attrib['type'] != 'fixed'
    }
    assert 'cell_robotiq_3f_finger_a_proximal_joint' in movable
    assert 'cell_robotiq_3f_finger_b_scissor_joint' in movable
    assert 'cell_robotiq_3f_finger_c_scissor_joint' in movable


def _control_root(*mappings):
    return ET.fromstring(_expand(
        'robot_ip:=127.0.0.1',
        *mappings,
        xacro_name='workcell_control.urdf.xacro',
    ))


def test_control_wrapper_uses_official_real_hardware_interface():
    """The real wrapper selects the official UR hardware plugin."""
    root = _control_root()
    control_systems = root.findall('ros2_control')

    assert len(control_systems) == 1
    plugin = control_systems[0].find('./hardware/plugin')
    assert plugin is not None
    assert plugin.text == 'ur_robot_driver/URPositionHardwareInterface'

    parameters = {
        element.attrib['name']: element.text
        for element in control_systems[0].findall('./hardware/param')
    }
    assert parameters['robot_ip'] == '127.0.0.1'
    assert parameters['kinematics/hash'] == _calibration()['hash']


def test_control_wrapper_supports_mock_hardware_without_changing_geometry():
    """Mock control retains the authoritative physical link chain."""
    root = _control_root('use_mock_hardware:=true')
    plugin = root.find('./ros2_control/hardware/plugin')
    assert plugin is not None
    assert plugin.text == 'mock_components/GenericSystem'

    links = {element.attrib['name'] for element in root.findall('link')}
    required_links = {
        'world',
        'base_link',
        'tool0',
        'ft_measurement_frame',
        'grasp_tcp',
    }
    assert required_links <= links


def test_tcp_x_points_out_of_reference_tactile_surface_in_both_wrappers():
    """Fixed TCP X matches the Basic/open tactile normal, not its tangent."""
    for root in (ET.fromstring(_expand()), _control_root()):
        xyz, (roll, pitch, yaw) = _origin(root, 'grasp_tcp_joint')
        _assert_vector(
            xyz,
            (-0.05091168824543142, 0.05091168824543142, 0.275),
        )
        _assert_vector((roll, pitch), (0, 0))
        _assert_vector(
            (math.cos(yaw), math.sin(yaw), 0),
            (math.sqrt(0.5), -math.sqrt(0.5), 0),
        )
