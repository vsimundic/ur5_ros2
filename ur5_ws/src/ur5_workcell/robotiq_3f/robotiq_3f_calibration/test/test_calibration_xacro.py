# Copyright 2026 UR5 ROS 2 maintainers

from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import pytest


@pytest.fixture(scope='module')
def calibration_joints():
    xacro_file = Path(__file__).parents[1] / 'urdf' / 'calibration_gripper.urdf.xacro'
    result = subprocess.run(
        ['xacro', str(xacro_file)],
        check=True,
        capture_output=True,
        text=True,
    )
    root = ET.fromstring(result.stdout)
    return {joint.attrib['name']: joint for joint in root.findall('joint')}


def test_each_middle_pivot_has_three_sources_and_opposed_mimics(calibration_joints):
    for finger in ('a', 'b', 'c'):
        base = f'robotiq_3f_finger_{finger}_middle_joint'
        for axis in ('x', 'y', 'z'):
            source = calibration_joints[f'{base}_pivot_{axis}_joint']
            compensation = calibration_joints[f'{base}_compensate_{axis}_joint']
            assert source.attrib['type'] == 'prismatic'
            assert compensation.attrib['type'] == 'prismatic'
            mimic = compensation.find('mimic')
            assert mimic.attrib == {
                'joint': f'{base}_pivot_{axis}_joint',
                'multiplier': '-1',
            }


def test_calibration_chain_preserves_public_middle_joint_names(calibration_joints):
    for finger in ('a', 'b', 'c'):
        name = f'robotiq_3f_finger_{finger}_middle_joint'
        joint = calibration_joints[name]
        assert joint.attrib['type'] == 'revolute'
        assert joint.find('origin').attrib['xyz'] == '0 0 0'
        assert joint.find('parent').attrib['link'] == f'{name}_pivot_z_link'
