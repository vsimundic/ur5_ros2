"""Domain model tests."""

from math import nan

import pytest

from robots_and_cubes_game.models import (
    Board,
    GameCoordinate,
    GameMode,
    GridCell,
    Handedness,
    QuarterTurn,
)


def test_mode_definitions_are_complete_and_stable():
    assert {mode.value for mode in GameMode} == {
        'easy', 'beginner', 'standard', 'challenge'
    }


def test_orientation_definitions_are_complete_and_stable():
    assert {int(rotation) for rotation in QuarterTurn} == {0, 90, 180, 270}
    assert {handedness.value for handedness in Handedness} == {'right', 'left'}


@pytest.mark.parametrize('values', [(1.2, 1), (True, 1), (1, False)])
def test_grid_cells_reject_non_integer_indices(values):
    with pytest.raises(TypeError):
        GridCell(*values)


@pytest.mark.parametrize('values', [(1.2, 1), (True, 1), (1, False)])
def test_game_coordinates_reject_non_integer_values(values):
    with pytest.raises(TypeError):
        GameCoordinate(*values)


@pytest.mark.parametrize(
    'values',
    [(1, 6, 0.09), (6, 1, 0.09), (6, 6, 0.0), (6, 6, nan), (True, 6, 0.09)],
)
def test_board_rejects_invalid_geometry(values):
    with pytest.raises(ValueError):
        Board(*values)
