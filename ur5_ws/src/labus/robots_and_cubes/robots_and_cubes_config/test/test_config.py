"""Configuration validation tests."""

from copy import deepcopy
from pathlib import Path

import pytest

from robots_and_cubes_config import (
    ConfigError,
    load_robot_commissioning,
    load_user_settings,
)
import yaml


PROJECT_ROOT = Path(__file__).parents[2]
USER_CONFIG = PROJECT_ROOT / 'config' / 'user_settings.yaml'
ROBOT_CONFIG = PROJECT_ROOT / 'config' / 'robot_commissioning.yaml'


def _user_data():
    return yaml.safe_load(USER_CONFIG.read_text(encoding='utf-8'))


def _write(tmp_path, data):
    path = tmp_path / 'config.yaml'
    path.write_text(yaml.safe_dump(data), encoding='utf-8')
    return path


def test_default_user_settings_load():
    settings = load_user_settings(USER_CONFIG)
    assert settings.application_name == 'Robots and Cubes'
    assert settings.execution_mode == 'MOCK'
    assert settings.board.rows == 6
    assert settings.board.columns == 6
    assert settings.board.cell_size_m == 0.09
    assert settings.game.cubes.red_count == 1
    assert settings.game.cubes.green_count == 1
    assert settings.game.cubes.blue_count == 1
    assert settings.game.cubes.black_count == 1
    assert settings.game.cubes.white_count == 1
    assert settings.game.cubes.total == 5
    assert settings.game.attempts == 2
    assert settings.game.standard.central_origin_margin_cells == 1
    assert (settings.game.spatial.origin_column, settings.game.spatial.origin_row) == (2, 2)
    assert settings.game.challenge.rotations_deg == (0, 90, 180, 270)


def test_default_commissioning_loads_but_is_not_execution_ready():
    settings = load_robot_commissioning(ROBOT_CONFIG)
    assert settings.frames.task_reference_frame == 'base_link'
    assert settings.frames.moveit_planning_frame == 'world'
    assert settings.robot.planning_group == 'ur_manipulator'
    assert settings.robot.planning_end_link == 'tool0'
    assert settings.task_tcp.frame_name == 'cube_grasp_tcp'
    assert settings.task_tcp.parent_frame == 'tool0'
    assert settings.task_tcp.translation_m == (0.0, 0.0, 0.275)
    assert settings.task_tcp.orientation_rpy_rad == (
        0.0, 0.0, -0.7853981633974483
    )
    assert settings.calibration_pen.parent_frame == 'tool0'
    assert settings.calibration_pen.tip_translation_m == (0.0, 0.0, 0.315)
    assert settings.motion.fallback_planner_id == 'RRTstarkConfigDefault'
    assert settings.gripper.command_action == '/robotiq_3f/gripper_command'
    assert settings.gripper.status_topic == '/robotiq_3f/status'
    assert not settings.real_execution_ready


@pytest.mark.parametrize(
    ('keys', 'value'),
    [
        (('game', 'cubes', 'red_count'), -1),
        (('game', 'cubes', 'green_count'), 2),
        (('game', 'attempts'), 0),
        (('board', 'rows'), 1),
        (('board', 'columns'), 1),
        (('board', 'cell_size_m'), 0),
        (('cube', 'size_m', 'x'), 0.10),
        (('cube', 'size_m', 'z'), float('nan')),
        (('mock', 'movement_duration_seconds'), 0),
        (('generation', 'maximum_attempts'), 0),
    ],
)
def test_invalid_numeric_user_values_are_rejected(tmp_path, keys, value):
    data = _user_data()
    target = data
    for key in keys[:-1]:
        target = target[key]
    target[keys[-1]] = value
    with pytest.raises(ConfigError):
        load_user_settings(_write(tmp_path, data))


def test_impossible_cube_and_origin_capacity_is_rejected(tmp_path):
    data = _user_data()
    data['board']['rows'] = 2
    data['board']['columns'] = 2
    with pytest.raises(ConfigError, match='room for all pieces'):
        load_user_settings(_write(tmp_path, data))


def test_impossible_standard_margin_is_rejected(tmp_path):
    data = _user_data()
    data['game']['standard']['central_origin_margin_cells'] = 3
    with pytest.raises(ConfigError, match='leaves no Standard origin'):
        load_user_settings(_write(tmp_path, data))


def test_spatial_origin_outside_board_is_rejected(tmp_path):
    data = _user_data()
    data['game']['spatial']['origin_column'] = 6
    with pytest.raises(ConfigError, match='Spatial origin must be inside'):
        load_user_settings(_write(tmp_path, data))


@pytest.mark.parametrize('rotations', [[45], [], [0, 90, 90]])
def test_invalid_challenge_rotations_are_rejected(tmp_path, rotations):
    data = _user_data()
    data['game']['challenge']['rotations_deg'] = rotations
    with pytest.raises(ConfigError):
        load_user_settings(_write(tmp_path, data))


def test_duplicate_or_unknown_modes_are_rejected(tmp_path):
    for modes in (['easy', 'easy'], ['easy', 'expert']):
        data = _user_data()
        data['game']['enabled_modes'] = modes
        with pytest.raises(ConfigError):
            load_user_settings(_write(tmp_path, data))


def test_user_configuration_cannot_contain_low_level_robot_fields(tmp_path):
    data = _user_data()
    data['robot'] = {'robot_ip': '127.0.0.1'}
    with pytest.raises(ConfigError, match='root unknown: robot'):
        load_user_settings(_write(tmp_path, data))


def test_unknown_nested_property_is_rejected(tmp_path):
    data = _user_data()
    data['board']['width'] = 6
    with pytest.raises(ConfigError, match='board unknown: width'):
        load_user_settings(_write(tmp_path, data))


def test_execution_mode_is_explicit_and_closed_to_unknown_values(tmp_path):
    data = _user_data()
    data['application']['execution_mode'] = 'UNSAFE'
    with pytest.raises(ConfigError, match='execution_mode supports only'):
        load_user_settings(_write(tmp_path, data))


def test_non_boolean_is_not_coerced(tmp_path):
    data = _user_data()
    data['generation']['allow_adjacent_cubes'] = 'true'
    with pytest.raises(ConfigError, match='must be a boolean'):
        load_user_settings(_write(tmp_path, data))


def test_disabled_adjacency_requires_two_cell_manhattan_distance(tmp_path):
    data = _user_data()
    data['generation']['allow_adjacent_cubes'] = False
    with pytest.raises(ConfigError, match='must be >= 2'):
        load_user_settings(_write(tmp_path, data))


def test_touchscreen_answer_limit_is_enforced(tmp_path):
    data = _user_data()
    data['game']['cubes']['red_count'] = 2
    with pytest.raises(ConfigError, match='exactly one piece'):
        load_user_settings(_write(tmp_path, data))


def test_commissioned_limits_are_validated(tmp_path):
    data = yaml.safe_load(ROBOT_CONFIG.read_text(encoding='utf-8'))
    data['motion'].update({
        'primary_pipeline': 'pilz_industrial_motion_planner',
        'allowed_joint_ranges_rad': {'joint_a': [-1.0, 1.0]},
        'maximum_joint_excursion_rad': {'joint_a': 0.5},
        'default_grasp_yaw_deg': 0.0,
    })
    data['gripper'].update({
        'open_position_m': 0.1,
        'cube_close_position_m': 0.03,
        'cube_effort_n': 30.0,
    })
    settings = load_robot_commissioning(_write(tmp_path, data))
    assert settings.real_execution_ready

    bad = deepcopy(data)
    bad['motion']['allowed_joint_ranges_rad']['joint_a'] = [1.0, -1.0]
    with pytest.raises(ConfigError, match='minimum must be below maximum'):
        load_robot_commissioning(_write(tmp_path, bad))


@pytest.mark.parametrize(
    ('section', 'field', 'value'),
    [
        ('task_tcp', 'translation_m', [0.0, 0.0]),
        ('task_tcp', 'orientation_rpy_rad', [0.0, float('nan'), 0.0]),
        ('calibration_pen', 'tip_translation_m', [0.0, 0.315]),
    ],
)
def test_application_geometry_requires_finite_three_vectors(
    tmp_path, section, field, value
):
    data = yaml.safe_load(ROBOT_CONFIG.read_text(encoding='utf-8'))
    data[section][field] = value
    with pytest.raises(ConfigError, match='must contain 3|finite number'):
        load_robot_commissioning(_write(tmp_path, data))


def test_legacy_nullable_tcp_fields_are_rejected(tmp_path):
    data = yaml.safe_load(ROBOT_CONFIG.read_text(encoding='utf-8'))
    data['motion']['task_tcp_frame'] = None
    with pytest.raises(ConfigError, match='motion unknown: task_tcp_frame'):
        load_robot_commissioning(_write(tmp_path, data))
