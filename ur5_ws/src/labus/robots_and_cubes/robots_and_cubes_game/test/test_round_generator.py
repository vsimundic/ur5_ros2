from dataclasses import replace

import pytest

from robots_and_cubes_game.models import CubeKind, GameMode, Handedness, QuarterTurn
from robots_and_cubes_game.round_generator import RoundGenerationError, RoundGenerator


def _manhattan(first, second):
    return abs(first.column - second.column) + abs(first.row - second.row)


def test_two_thousand_seeded_rounds_obey_all_invariants(settings):
    generator = RoundGenerator(settings)
    seen_challenge_rotations = set()
    seen_challenge_handedness = set()
    for mode in GameMode:
        for seed in range(500):
            game_round = generator.generate(mode, seed)
            cells = [cube.cell for cube in game_round.cubes]
            coordinates = [cube.game_coordinate for cube in game_round.cubes]

            assert game_round.random_seed == seed
            assert len(game_round.cubes) == settings.game.cubes.total
            assert sum(cube.kind is CubeKind.RED for cube in game_round.cubes) == 4
            assert sum(cube.kind is CubeKind.GREEN for cube in game_round.cubes) == 1
            assert game_round.green_cube_id == 'green_1'
            assert len(set(cells)) == len(cells)
            assert len(set(coordinates)) == len(coordinates)
            assert game_round.origin_cell not in cells
            assert set(game_round.answer_order) == {
                cube.cube_id for cube in game_round.cubes
            }
            assert game_round.attempts == settings.game.attempts
            for first_index, first in enumerate(cells):
                for second in cells[first_index + 1:]:
                    assert _manhattan(first, second) >= 1

            if mode is GameMode.STANDARD:
                margin = settings.game.standard.central_origin_margin_cells
                assert margin <= game_round.origin_cell.column < 6 - margin
                assert margin <= game_round.origin_cell.row < 6 - margin
            if mode is GameMode.CHALLENGE:
                seen_challenge_rotations.add(game_round.rotation)
                seen_challenge_handedness.add(game_round.handedness)
            else:
                assert game_round.rotation is QuarterTurn.DEG_0
                assert game_round.handedness is Handedness.RIGHT
            if mode is GameMode.BEGINNER:
                assert game_round.beginner_target_cube_id in game_round.answer_order
            else:
                assert game_round.beginner_target_cube_id is None

    assert seen_challenge_rotations == set(QuarterTurn)
    assert seen_challenge_handedness == set(Handedness)


def test_default_standard_origins_are_exactly_the_central_four_by_four(settings):
    generator = RoundGenerator(settings)
    origins = set(generator.origin_cells(GameMode.STANDARD))
    expected = {
        type(next(iter(origins)))(column, row)
        for column in range(1, 5)
        for row in range(1, 5)
    }
    assert origins == expected


def test_nondefault_standard_margin_controls_legal_origins(settings):
    standard = replace(settings.game.standard, central_origin_margin_cells=2)
    game = replace(settings.game, standard=standard)
    generator = RoundGenerator(replace(settings, game=game))
    assert set(generator.origin_cells(GameMode.STANDARD)) == {
        type(generator.origin_cells(GameMode.STANDARD)[0])(column, row)
        for column in range(2, 4)
        for row in range(2, 4)
    }
    assert all(
        generated.origin_cell in generator.origin_cells(GameMode.STANDARD)
        for generated in (
            generator.generate(GameMode.STANDARD, seed) for seed in range(100)
        )
    )


def test_challenge_respects_configured_orientation_subset(settings):
    challenge = replace(
        settings.game.challenge,
        rotations_deg=(90, 270),
        enable_left_handed=False,
    )
    game = replace(settings.game, challenge=challenge)
    generator = RoundGenerator(replace(settings, game=game))
    rounds = [generator.generate(GameMode.CHALLENGE, seed) for seed in range(100)]
    assert {game_round.rotation for game_round in rounds} == {
        QuarterTurn.DEG_90, QuarterTurn.DEG_270
    }
    assert {game_round.handedness for game_round in rounds} == {Handedness.RIGHT}


def test_same_seed_and_mode_reproduce_complete_round(settings):
    generator = RoundGenerator(settings)
    assert generator.generate(GameMode.CHALLENGE, 92831) == generator.generate(
        GameMode.CHALLENGE, 92831
    )


def test_disabled_mode_is_rejected(settings):
    game = replace(settings.game, enabled_modes=('easy',))
    generator = RoundGenerator(replace(settings, game=game))
    with pytest.raises(RoundGenerationError, match='mode is disabled'):
        generator.generate(GameMode.STANDARD, 1)


def test_required_coordinate_signs_are_enforced(settings):
    generation = replace(
        settings.generation,
        require_positive_x=True,
        require_negative_x=True,
        require_positive_y=True,
        require_negative_y=True,
    )
    game_round = RoundGenerator(replace(settings, generation=generation)).generate(
        GameMode.STANDARD, 42
    )
    coordinates = [cube.game_coordinate for cube in game_round.cubes]
    assert any(coordinate.x > 0 for coordinate in coordinates)
    assert any(coordinate.x < 0 for coordinate in coordinates)
    assert any(coordinate.y > 0 for coordinate in coordinates)
    assert any(coordinate.y < 0 for coordinate in coordinates)


def test_nonadjacent_setting_enforces_manhattan_distance(settings):
    generation = replace(
        settings.generation,
        allow_adjacent_cubes=False,
        minimum_cell_distance=2,
    )
    game_round = RoundGenerator(replace(settings, generation=generation)).generate(
        GameMode.CHALLENGE, 171
    )
    cells = [cube.cell for cube in game_round.cubes]
    assert all(
        _manhattan(first, second) >= 2
        for index, first in enumerate(cells)
        for second in cells[index + 1:]
    )


def test_impossible_generation_fails_at_configured_bound(settings):
    generation = replace(
        settings.generation,
        minimum_cell_distance=20,
        maximum_attempts=3,
    )
    generator = RoundGenerator(replace(settings, generation=generation))
    with pytest.raises(RoundGenerationError, match='could not generate'):
        generator.generate(GameMode.STANDARD, 1)


def test_seed_must_be_integer(settings):
    with pytest.raises(TypeError):
        RoundGenerator(settings).generate(GameMode.EASY, True)
