"""Architecture checks that keep the application mock hardware-free."""

from pathlib import Path
from xml.etree import ElementTree


def test_mock_package_declares_no_hardware_or_planning_dependency():
    root = Path(__file__).parents[1]
    package = ElementTree.parse(root / 'package.xml').getroot()
    dependencies = {node.text for node in package.findall('./*') if node.tag.endswith('depend')}
    forbidden = {
        'ur_robot_driver', 'ur5_workcell_bringup', 'moveit_ros_planning_interface',
        'robotiq_3f_driver', 'robotiq_3f_controller', 'robotiq_ft_streamer',
        'ur5_workcell_sim',
    }
    assert not dependencies & forbidden
