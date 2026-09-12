import pytest

from robots_and_cubes_game.coordinates import (
    game_to_grid,
    grid_to_game,
    transform_matrix,
)
from robots_and_cubes_game.models import (
    Board,
    GameCoordinate,
    GridCell,
    Handedness,
    QuarterTurn,
)


EXPECTED = {
    (QuarterTurn.DEG_0, Handedness.RIGHT): ((1, 0), (0, 1)),
    (QuarterTurn.DEG_90, Handedness.RIGHT): ((0, -1), (1, 0)),
    (QuarterTurn.DEG_180, Handedness.RIGHT): ((-1, 0), (0, -1)),
    (QuarterTurn.DEG_270, Handedness.RIGHT): ((0, 1), (-1, 0)),
    (QuarterTurn.DEG_0, Handedness.LEFT): ((1, 0), (0, -1)),
    (QuarterTurn.DEG_90, Handedness.LEFT): ((0, 1), (1, 0)),
    (QuarterTurn.DEG_180, Handedness.LEFT): ((-1, 0), (0, 1)),
    (QuarterTurn.DEG_270, Handedness.LEFT): ((0, -1), (-1, 0)),
}


@pytest.mark.parametrize(('orientation', 'expected'), EXPECTED.items())
def test_exact_transform_matrices(orientation, expected):
    assert transform_matrix(*orientation) == expected


@pytest.mark.parametrize('rotation', list(QuarterTurn))
@pytest.mark.parametrize('handedness', list(Handedness))
def test_transform_is_orthogonal_with_expected_determinant(rotation, handedness):
    matrix = transform_matrix(rotation, handedness)
    row_0, row_1 = matrix
    assert sum(value * value for value in row_0) == 1
    assert sum(value * value for value in row_1) == 1
    assert sum(a * b for a, b in zip(row_0, row_1)) == 0
    determinant = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
    assert determinant == (1 if handedness is Handedness.RIGHT else -1)


def test_every_cell_origin_rotation_and_handedness_round_trips():
    board = Board(rows=6, columns=6, cell_size_m=0.09)
    checked = 0
    for origin in board.cells():
        for cell in board.cells():
            for rotation in QuarterTurn:
                for handedness in Handedness:
                    coordinate = grid_to_game(cell, origin, rotation, handedness)
                    assert isinstance(coordinate.x, int)
                    assert isinstance(coordinate.y, int)
                    assert game_to_grid(
                        coordinate, origin, rotation, handedness
                    ) == cell
                    checked += 1
    assert checked == 36 * 36 * 4 * 2


def test_every_coordinate_in_board_extent_round_trips_without_rounding():
    origin = GridCell(3, 2)
    for x in range(-5, 6):
        for y in range(-5, 6):
            coordinate = GameCoordinate(x, y)
            for rotation in QuarterTurn:
                for handedness in Handedness:
                    cell = game_to_grid(
                        coordinate, origin, rotation, handedness
                    )
                    assert grid_to_game(
                        cell, origin, rotation, handedness
                    ) == coordinate


def test_board_cell_centers_and_bounds():
    board = Board(6, 6, 0.09)
    assert board.cell_center_m(GridCell(0, 0)) == (0.045, 0.045)
    assert board.cell_center_m(GridCell(5, 5)) == (0.495, 0.495)
    assert board.contains(GridCell(5, 5))
    assert not board.contains(GridCell(6, 5))
    with pytest.raises(ValueError):
        board.cell_center_m(GridCell(-1, 0))
