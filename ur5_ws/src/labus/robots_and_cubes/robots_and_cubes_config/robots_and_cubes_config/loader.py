"""Strict YAML loading for Robots and Cubes configuration."""

from math import isfinite, sqrt
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from .models import (
    BoardSettings,
    ChallengeSettings,
    ConfigError,
    CubeCounts,
    CubeSettings,
    GameSettings,
    GenerationSettings,
    GripperCommissioning,
    JointLimit,
    MAX_TOUCHSCREEN_ANSWERS,
    MockSettings,
    MotionCommissioning,
    RigidTransform,
    RobotCommissioning,
    RobotIdentity,
    Size3D,
    StandardSettings,
    SUPPORTED_MODES,
    SUPPORTED_ROTATIONS,
    UserSettings,
)


def _read_yaml(path: Path) -> Mapping[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding='utf-8'))
    except (OSError, yaml.YAMLError) as error:
        raise ConfigError(f'{path}: cannot load YAML: {error}') from error
    if not isinstance(value, dict):
        raise ConfigError(f'{path}: root must be a mapping')
    return value


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f'{path} must be a mapping')
    return value


def _exact(mapping: Mapping[str, Any], keys: Sequence[str], path: str) -> None:
    expected = set(keys)
    actual = set(mapping)
    if missing := expected - actual:
        raise ConfigError(f'{path} missing: {", ".join(sorted(missing))}')
    if unknown := actual - expected:
        raise ConfigError(f'{path} unknown: {", ".join(sorted(unknown))}')


def _integer(value: Any, path: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ConfigError(f'{path} must be an integer >= {minimum}')
    return value


def _number(value: Any, path: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f'{path} must be a finite number')
    result = float(value)
    if not isfinite(result) or (positive and result <= 0.0):
        qualifier = 'positive finite' if positive else 'finite'
        raise ConfigError(f'{path} must be a {qualifier} number')
    return result


def _boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f'{path} must be a boolean')
    return value


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f'{path} must be a non-empty string')
    return value


def _optional_string(value: Any, path: str) -> str | None:
    return None if value is None else _string(value, path)


def load_user_settings(path: str | Path) -> UserSettings:
    """Load and cross-validate a normal user configuration file."""
    root = _read_yaml(Path(path))
    _exact(
        root,
        ('schema_version', 'application', 'game', 'board', 'cube', 'generation', 'mock'),
        'root',
    )
    schema_version = _integer(root['schema_version'], 'schema_version', 1)
    if schema_version != 1:
        raise ConfigError('schema_version must be 1')

    application = _mapping(root['application'], 'application')
    _exact(application, ('name',), 'application')
    application_name = _string(application['name'], 'application.name')

    board_data = _mapping(root['board'], 'board')
    _exact(board_data, ('rows', 'columns', 'cell_size_m'), 'board')
    board = BoardSettings(
        rows=_integer(board_data['rows'], 'board.rows', 2),
        columns=_integer(board_data['columns'], 'board.columns', 2),
        cell_size_m=_number(board_data['cell_size_m'], 'board.cell_size_m', positive=True),
    )

    cube_data = _mapping(root['cube'], 'cube')
    _exact(cube_data, ('size_m',), 'cube')
    size_data = _mapping(cube_data['size_m'], 'cube.size_m')
    _exact(size_data, ('x', 'y', 'z'), 'cube.size_m')
    cube = CubeSettings(Size3D(**{
        axis: _number(size_data[axis], f'cube.size_m.{axis}', positive=True)
        for axis in ('x', 'y', 'z')
    }))
    if cube.size_m.x > board.cell_size_m or cube.size_m.y > board.cell_size_m:
        raise ConfigError('cube x/y size cannot exceed board.cell_size_m')

    game_data = _mapping(root['game'], 'game')
    _exact(game_data, ('enabled_modes', 'attempts', 'cubes', 'standard', 'challenge'), 'game')
    modes_value = game_data['enabled_modes']
    if not isinstance(modes_value, list) or not modes_value:
        raise ConfigError('game.enabled_modes must be a non-empty list')
    modes = tuple(modes_value)
    if any(not isinstance(mode, str) or mode not in SUPPORTED_MODES for mode in modes):
        raise ConfigError(f'game.enabled_modes supports only {SUPPORTED_MODES}')
    if len(set(modes)) != len(modes):
        raise ConfigError('game.enabled_modes cannot contain duplicates')

    counts_data = _mapping(game_data['cubes'], 'game.cubes')
    _exact(counts_data, ('red_count', 'green_count'), 'game.cubes')
    counts = CubeCounts(
        red_count=_integer(counts_data['red_count'], 'game.cubes.red_count', 1),
        green_count=_integer(counts_data['green_count'], 'game.cubes.green_count', 1),
    )
    if counts.green_count != 1:
        raise ConfigError('game.cubes.green_count must equal 1')
    if counts.total > MAX_TOUCHSCREEN_ANSWERS:
        raise ConfigError(
            f'total cube count cannot exceed {MAX_TOUCHSCREEN_ANSWERS}'
        )
    if counts.total + 1 > board.cell_count:
        raise ConfigError('board needs one origin cell plus all cube cells')

    standard_data = _mapping(game_data['standard'], 'game.standard')
    _exact(standard_data, ('central_origin_margin_cells',), 'game.standard')
    margin = _integer(
        standard_data['central_origin_margin_cells'],
        'game.standard.central_origin_margin_cells',
        0,
    )
    if 2 * margin >= board.rows or 2 * margin >= board.columns:
        raise ConfigError('central origin margin leaves no Standard origin cells')

    challenge_data = _mapping(game_data['challenge'], 'game.challenge')
    _exact(challenge_data, ('rotations_deg', 'enable_left_handed'), 'game.challenge')
    rotation_values = challenge_data['rotations_deg']
    if not isinstance(rotation_values, list) or not rotation_values:
        raise ConfigError('game.challenge.rotations_deg must be a non-empty list')
    rotations = tuple(rotation_values)
    if any(
        isinstance(rotation, bool) or rotation not in SUPPORTED_ROTATIONS
        for rotation in rotations
    ):
        raise ConfigError(
            f'game.challenge.rotations_deg supports only {SUPPORTED_ROTATIONS}'
        )
    if len(set(rotations)) != len(rotations):
        raise ConfigError('game.challenge.rotations_deg cannot contain duplicates')

    game = GameSettings(
        enabled_modes=modes,
        attempts=_integer(game_data['attempts'], 'game.attempts', 1),
        cubes=counts,
        standard=StandardSettings(margin),
        challenge=ChallengeSettings(
            rotations,
            _boolean(
                challenge_data['enable_left_handed'],
                'game.challenge.enable_left_handed',
            ),
        ),
    )

    generation_data = _mapping(root['generation'], 'generation')
    generation_keys = (
        'allow_adjacent_cubes', 'minimum_cell_distance',
        'favor_coordinate_sign_variety', 'require_positive_x',
        'require_negative_x', 'require_positive_y', 'require_negative_y',
        'maximum_attempts',
    )
    _exact(generation_data, generation_keys, 'generation')
    minimum_distance = _integer(
        generation_data['minimum_cell_distance'],
        'generation.minimum_cell_distance',
        1,
    )
    allow_adjacent = _boolean(
        generation_data['allow_adjacent_cubes'],
        'generation.allow_adjacent_cubes',
    )
    if not allow_adjacent and minimum_distance < 2:
        raise ConfigError(
            'generation.minimum_cell_distance must be >= 2 when adjacency is disabled'
        )
    generation = GenerationSettings(
        allow_adjacent_cubes=allow_adjacent,
        minimum_cell_distance=minimum_distance,
        favor_coordinate_sign_variety=_boolean(
            generation_data['favor_coordinate_sign_variety'],
            'generation.favor_coordinate_sign_variety',
        ),
        require_positive_x=_boolean(
            generation_data['require_positive_x'], 'generation.require_positive_x'
        ),
        require_negative_x=_boolean(
            generation_data['require_negative_x'], 'generation.require_negative_x'
        ),
        require_positive_y=_boolean(
            generation_data['require_positive_y'], 'generation.require_positive_y'
        ),
        require_negative_y=_boolean(
            generation_data['require_negative_y'], 'generation.require_negative_y'
        ),
        maximum_attempts=_integer(
            generation_data['maximum_attempts'], 'generation.maximum_attempts', 1
        ),
    )

    mock_data = _mapping(root['mock'], 'mock')
    _exact(mock_data, ('movement_duration_seconds',), 'mock')
    mock = MockSettings(_number(
        mock_data['movement_duration_seconds'],
        'mock.movement_duration_seconds',
        positive=True,
    ))
    return UserSettings(
        schema_version, application_name, game, board, cube, generation, mock
    )


def _optional_transform(value: Any, path: str) -> RigidTransform | None:
    if value is None:
        return None
    data = _mapping(value, path)
    _exact(data, ('translation_m', 'rotation_xyzw'), path)
    translation = data['translation_m']
    rotation = data['rotation_xyzw']
    if not isinstance(translation, list) or len(translation) != 3:
        raise ConfigError(f'{path}.translation_m must contain 3 values')
    if not isinstance(rotation, list) or len(rotation) != 4:
        raise ConfigError(f'{path}.rotation_xyzw must contain 4 values')
    xyz = tuple(_number(value, f'{path}.translation_m') for value in translation)
    xyzw = tuple(_number(value, f'{path}.rotation_xyzw') for value in rotation)
    norm = sqrt(sum(component * component for component in xyzw))
    if abs(norm - 1.0) > 1e-6:
        raise ConfigError(f'{path}.rotation_xyzw must be a unit quaternion')
    return RigidTransform(xyz, xyzw)


def _optional_joint_ranges(value: Any, path: str) -> tuple[JointLimit, ...] | None:
    if value is None:
        return None
    data = _mapping(value, path)
    if not data:
        raise ConfigError(f'{path} cannot be empty')
    limits = []
    for name, raw_range in sorted(data.items()):
        _string(name, f'{path} joint name')
        if not isinstance(raw_range, list) or len(raw_range) != 2:
            raise ConfigError(f'{path}.{name} must be [minimum, maximum]')
        minimum = _number(raw_range[0], f'{path}.{name}[0]')
        maximum = _number(raw_range[1], f'{path}.{name}[1]')
        if minimum >= maximum:
            raise ConfigError(f'{path}.{name} minimum must be below maximum')
        limits.append(JointLimit(name, minimum, maximum))
    return tuple(limits)


def _optional_excursions(value: Any, path: str) -> tuple[tuple[str, float], ...] | None:
    if value is None:
        return None
    data = _mapping(value, path)
    if not data:
        raise ConfigError(f'{path} cannot be empty')
    return tuple(
        (name, _number(limit, f'{path}.{name}', positive=True))
        for name, limit in sorted(data.items())
        if _string(name, f'{path} joint name')
    )


def load_robot_commissioning(path: str | Path) -> RobotCommissioning:
    """Load advanced commissioning data without supplying missing values."""
    root = _read_yaml(Path(path))
    _exact(root, ('schema_version', 'robot', 'motion', 'gripper'), 'root')
    schema_version = _integer(root['schema_version'], 'schema_version', 1)
    if schema_version != 1:
        raise ConfigError('schema_version must be 1')

    robot_data = _mapping(root['robot'], 'robot')
    robot_keys = ('base_frame', 'planning_frame', 'planning_group', 'planning_end_link')
    _exact(robot_data, robot_keys, 'robot')
    robot = RobotIdentity(**{
        key: _string(robot_data[key], f'robot.{key}') for key in robot_keys
    })

    motion_data = _mapping(root['motion'], 'motion')
    motion_keys = (
        'primary_pipeline', 'fallback_pipeline', 'fallback_planner_id',
        'task_tcp_frame', 'tool_to_pen_tip', 'allowed_joint_ranges_rad',
        'maximum_joint_excursion_rad', 'default_grasp_yaw_deg',
    )
    _exact(motion_data, motion_keys, 'motion')
    yaw = motion_data['default_grasp_yaw_deg']
    motion = MotionCommissioning(
        primary_pipeline=_optional_string(
            motion_data['primary_pipeline'], 'motion.primary_pipeline'
        ),
        fallback_pipeline=_optional_string(
            motion_data['fallback_pipeline'], 'motion.fallback_pipeline'
        ),
        fallback_planner_id=_optional_string(
            motion_data['fallback_planner_id'], 'motion.fallback_planner_id'
        ),
        task_tcp_frame=_optional_string(
            motion_data['task_tcp_frame'], 'motion.task_tcp_frame'
        ),
        tool_to_pen_tip=_optional_transform(
            motion_data['tool_to_pen_tip'], 'motion.tool_to_pen_tip'
        ),
        allowed_joint_ranges_rad=_optional_joint_ranges(
            motion_data['allowed_joint_ranges_rad'],
            'motion.allowed_joint_ranges_rad',
        ),
        maximum_joint_excursion_rad=_optional_excursions(
            motion_data['maximum_joint_excursion_rad'],
            'motion.maximum_joint_excursion_rad',
        ),
        default_grasp_yaw_deg=(
            None if yaw is None else _number(yaw, 'motion.default_grasp_yaw_deg')
        ),
    )

    gripper_data = _mapping(root['gripper'], 'gripper')
    gripper_keys = (
        'command_action', 'status_topic', 'open_position_m',
        'cube_close_position_m', 'cube_effort_n',
    )
    _exact(gripper_data, gripper_keys, 'gripper')
    optional_numbers = {}
    for key in ('open_position_m', 'cube_close_position_m', 'cube_effort_n'):
        value = gripper_data[key]
        optional_numbers[key] = None if value is None else _number(
            value, f'gripper.{key}', positive=key == 'cube_effort_n'
        )
    gripper = GripperCommissioning(
        command_action=_string(gripper_data['command_action'], 'gripper.command_action'),
        status_topic=_string(gripper_data['status_topic'], 'gripper.status_topic'),
        **optional_numbers,
    )
    return RobotCommissioning(schema_version, robot, motion, gripper)
