"""Offline checks for the application-only mock launch entry point."""

from importlib.util import module_from_spec, spec_from_file_location
import os
from pathlib import Path


def test_mock_launch_declares_only_the_application_mock_nodes(tmp_path):
    os.environ['ROS_LOG_DIR'] = str(tmp_path)
    path = Path(__file__).parents[1] / 'launch' / 'mock_game.launch.py'
    spec = spec_from_file_location('mock_game_launch', path)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    description = module.generate_launch_description()
    assert len(description.entities) == 11
