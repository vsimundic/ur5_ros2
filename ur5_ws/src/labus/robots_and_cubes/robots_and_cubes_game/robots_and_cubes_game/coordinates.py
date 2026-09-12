"""
Exact integer educational-coordinate transforms.

ROS frames remain right-handed. LEFT is represented only by the 2-D game
mapping H=diag(1,-1). For both handedness values A=R*H is orthogonal, so its
integer transpose is its inverse.
"""

from typing import Tuple

from .models import GameCoordinate, GridCell, Handedness, QuarterTurn


Matrix2 = Tuple[Tuple[int, int], Tuple[int, int]]

_ROTATIONS: dict[QuarterTurn, Matrix2] = {
    QuarterTurn.DEG_0: ((1, 0), (0, 1)),
    QuarterTurn.DEG_90: ((0, -1), (1, 0)),
    QuarterTurn.DEG_180: ((-1, 0), (0, -1)),
    QuarterTurn.DEG_270: ((0, 1), (-1, 0)),
}


def _multiply(left: Matrix2, right: Matrix2) -> Matrix2:
    return tuple(
        tuple(sum(left[row][k] * right[k][column] for k in range(2)) for column in range(2))
        for row in range(2)
    )  # type: ignore[return-value]


def transform_matrix(rotation: QuarterTurn, handedness: Handedness) -> Matrix2:
    """Return A=R(rotation)*H(handedness) using exact integers."""
    reflection: Matrix2 = (
        ((1, 0), (0, 1))
        if handedness is Handedness.RIGHT
        else ((1, 0), (0, -1))
    )
    return _multiply(_ROTATIONS[rotation], reflection)


def game_to_grid(
    coordinate: GameCoordinate,
    origin: GridCell,
    rotation: QuarterTurn,
    handedness: Handedness,
) -> GridCell:
    """Transform an educational coordinate into a board cell."""
    matrix = transform_matrix(rotation, handedness)
    delta_column = matrix[0][0] * coordinate.x + matrix[0][1] * coordinate.y
    delta_row = matrix[1][0] * coordinate.x + matrix[1][1] * coordinate.y
    return GridCell(origin.column + delta_column, origin.row + delta_row)


def grid_to_game(
    cell: GridCell,
    origin: GridCell,
    rotation: QuarterTurn,
    handedness: Handedness,
) -> GameCoordinate:
    """Transform a board cell into an educational coordinate."""
    matrix = transform_matrix(rotation, handedness)
    delta_column = cell.column - origin.column
    delta_row = cell.row - origin.row
    return GameCoordinate(
        matrix[0][0] * delta_column + matrix[1][0] * delta_row,
        matrix[0][1] * delta_column + matrix[1][1] * delta_row,
    )
