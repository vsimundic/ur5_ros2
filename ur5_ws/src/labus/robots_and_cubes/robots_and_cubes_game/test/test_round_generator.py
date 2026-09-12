from dataclasses import replace

import pytest

from robots_and_cubes_game.models import CubeKind, GameMode, Handedness, QuarterTurn
from robots_and_cubes_game.round_generator import RoundGenerationError, RoundGenerator


def _manhattan(first, second):
    return abs(first.column - second.column) + abs(first.row - second.row)


def test_seeded_rounds_obey_piece_and_origin_rules(settings):
    generator = RoundGenerator(settings)
    seen_challenge_rotations = set()
    seen_challenge_handedness = set()
    seen_challenge_targets = set()
    expected_kinds = set(CubeKind)
    for mode in GameMode:
        for seed in range(500):
            game_round = generator.generate(mode, seed)
            cells = [cube.cell for cube in game_round.cubes]
            coordinates = [cube.game_coordinate for cube in game_round.cubes]

            assert game_round.random_seed == seed
            assert len(game_round.cubes) == settings.game.cubes.total == 5
            assert {cube.kind for cube in game_round.cubes} == expected_kinds
            assert game_round.target_cube_id in {cube.cube_id for cube in game_round.cubes}
            assert len(set(cells)) == len(cells)
            assert len(set(coordinates)) == len(coordinates)
            assert set(game_round.answer_order) == {cube.cube_id for cube in game_round.cubes}
            assert game_round.attempts == settings.game.attempts
            for first_index, first in enumerate(cells):
                for second in cells[first_index + 1:]:
                    assert _manhattan(first, second) >= 1

            if mode in (GameMode.SPATIAL, GameMode.STANDARD, GameMode.CHALLENGE):
                assert game_round.origin_cell is not None
                assert game_round.origin_cell not in cells
            else:
                assert game_round.origin_cell is None
                assert game_round.rotation is QuarterTurn.DEG_0
                assert game_round.handedness is Handedness.RIGHT
            if mode is GameMode.SPATIAL:
                assert (game_round.origin_cell.column, game_round.origin_cell.row) == (2, 2)
            if mode is GameMode.STANDARD:
                margin = settings.game.standard.central_origin_margin_cells
                assert margin <= game_round.origin_cell.column < 6 - margin
                assert margin <= game_round.origin_cell.row < 6 - margin
            if mode is GameMode.STANDARD:
                assert game_round.target_cube_id == 'green_1'
            if mode is GameMode.CHALLENGE:
                seen_challenge_rotations.add(game_round.rotation)
                seen_challenge_handedness.add(game_round.handedness)
                seen_challenge_targets.add(game_round.target_cube_id)

    assert seen_challenge_rotations == set(QuarterTurn)
    assert seen_challenge_handedness == set(Handedness)
    assert seen_challenge_targets == {
        'green_1', 'blue_1', 'red_1', 'black_1', 'white_1',
    }


def test_spatial_rounds_use_the_configured_fixed_origin(settings):
    generator = RoundGenerator(settings)
    origin_cells = generator.origin_cells(GameMode.SPATIAL)
    assert {(cell.column, cell.row) for cell in origin_cells} == {(2, 2)}
    spatial = replace(settings.game.spatial, origin_column=3, origin_row=4)
    game = replace(settings.game, spatial=spatial)
    changed = RoundGenerator(replace(settings, game=game))
    changed_cells = changed.origin_cells(GameMode.SPATIAL)
    assert {(cell.column, cell.row) for cell in changed_cells} == {(3, 4)}


def test_default_standard_origins_are_the_central_four_by_four(settings):
    origins = RoundGenerator(settings).origin_cells(GameMode.STANDARD)
    assert {(cell.column, cell.row) for cell in origins} == {
        (column, row) for column in range(1, 5) for row in range(1, 5)
    }


def test_easy_and_beginner_can_use_every_cell_without_an_origin(settings):
    generator = RoundGenerator(settings)
    origin = (settings.game.spatial.origin_column, settings.game.spatial.origin_row)
    for mode in (GameMode.EASY, GameMode.BEGINNER):
        assert any(
            origin in {
                (cube.cell.column, cube.cell.row)
                for cube in generator.generate(mode, seed).cubes
            }
            for seed in range(100)
        )


def test_challenge_respects_configured_orientation_subset(settings):
    challenge = replace(settings.game.challenge, rotations_deg=(90, 270), enable_left_handed=False)
    game = replace(settings.game, challenge=challenge)
    generator = RoundGenerator(replace(settings, game=game))
    rounds = [generator.generate(GameMode.CHALLENGE, seed) for seed in range(100)]
    assert {game_round.rotation for game_round in rounds} == {
        QuarterTurn.DEG_90, QuarterTurn.DEG_270,
    }
    assert {game_round.handedness for game_round in rounds} == {Handedness.RIGHT}


def test_same_seed_and_mode_reproduce_complete_round(settings):
    generator = RoundGenerator(settings)
    assert generator.generate(GameMode.CHALLENGE, 92831) == generator.generate(
        GameMode.CHALLENGE, 92831
    )


def test_disabled_mode_is_rejected(settings):
    game = replace(settings.game, enabled_modes=('easy',))
    with pytest.raises(RoundGenerationError, match='mode is disabled'):
        RoundGenerator(replace(settings, game=game)).generate(GameMode.STANDARD, 1)


def test_required_coordinate_signs_are_enforced(settings):
    generation = replace(
        settings.generation,
        require_positive_x=True,
        require_negative_x=True,
        require_positive_y=True,
        require_negative_y=True,
    )
    generator = RoundGenerator(replace(settings, generation=generation))
    game_round = generator.generate(GameMode.STANDARD, 42)
    coordinates = [cube.game_coordinate for cube in game_round.cubes]
    assert any(coordinate.x > 0 for coordinate in coordinates)
    assert any(coordinate.x < 0 for coordinate in coordinates)
    assert any(coordinate.y > 0 for coordinate in coordinates)
    assert any(coordinate.y < 0 for coordinate in coordinates)


def test_nonadjacent_setting_enforces_manhattan_distance(settings):
    generation = replace(settings.generation, allow_adjacent_cubes=False, minimum_cell_distance=2)
    generator = RoundGenerator(replace(settings, generation=generation))
    cells = [cube.cell for cube in generator.generate(GameMode.CHALLENGE, 171).cubes]
    assert all(
        _manhattan(first, second) >= 2
        for index, first in enumerate(cells)
        for second in cells[index + 1:]
    )


def test_impossible_generation_fails_at_configured_bound(settings):
    generation = replace(settings.generation, minimum_cell_distance=20, maximum_attempts=3)
    with pytest.raises(RoundGenerationError, match='could not generate'):
        RoundGenerator(replace(settings, generation=generation)).generate(GameMode.STANDARD, 1)


def test_seed_must_be_integer(settings):
    with pytest.raises(TypeError):
        RoundGenerator(settings).generate(GameMode.EASY, True)
