"""Board, cube, coordinate, mode, and round domain models."""

from dataclasses import dataclass
from enum import Enum, IntEnum
from math import isfinite
from typing import Optional, Tuple


class GameMode(str, Enum):
    """Supported educational difficulty modes."""

    EASY = 'easy'
    BEGINNER = 'beginner'
    STANDARD = 'standard'
    CHALLENGE = 'challenge'


class Handedness(str, Enum):
    """Educational 2-D handedness; never a ROS TF handedness."""

    RIGHT = 'right'
    LEFT = 'left'


class QuarterTurn(IntEnum):
    """Supported exact game-axis rotations in degrees."""

    DEG_0 = 0
    DEG_90 = 90
    DEG_180 = 180
    DEG_270 = 270


class CubeKind(str, Enum):
    """Physical game cube role."""

    RED = 'red'
    GREEN = 'green'


@dataclass(frozen=True, order=True)
class GridCell:
    """Zero-based discrete board cell."""

    column: int
    row: int

    def __post_init__(self) -> None:
        """Require discrete integer board indices."""
        if (
            isinstance(self.column, bool)
            or not isinstance(self.column, int)
            or isinstance(self.row, bool)
            or not isinstance(self.row, int)
        ):
            raise TypeError('grid cell column and row must be integers')


@dataclass(frozen=True, order=True)
class GameCoordinate:
    """Exact integer coordinate in the educational axes."""

    x: int
    y: int

    def __post_init__(self) -> None:
        """Require exact integer educational coordinates."""
        if (
            isinstance(self.x, bool)
            or not isinstance(self.x, int)
            or isinstance(self.y, bool)
            or not isinstance(self.y, int)
        ):
            raise TypeError('game coordinate x and y must be integers')


@dataclass(frozen=True)
class Board:
    """Rectangular board whose objects occupy cell centers."""

    rows: int
    columns: int
    cell_size_m: float

    def __post_init__(self) -> None:
        """Validate discrete dimensions and finite positive cell pitch."""
        if (
            isinstance(self.rows, bool)
            or not isinstance(self.rows, int)
            or isinstance(self.columns, bool)
            or not isinstance(self.columns, int)
            or self.rows < 2
            or self.columns < 2
            or isinstance(self.cell_size_m, bool)
            or not isinstance(self.cell_size_m, (int, float))
            or not isfinite(self.cell_size_m)
            or self.cell_size_m <= 0.0
        ):
            raise ValueError('board requires >= 2 rows/columns and positive pitch')

    def contains(self, cell: GridCell) -> bool:
        """Return whether a cell belongs to this board."""
        return 0 <= cell.column < self.columns and 0 <= cell.row < self.rows

    def cells(self) -> Tuple[GridCell, ...]:
        """Return all cells in stable row-major order."""
        return tuple(
            GridCell(column, row)
            for row in range(self.rows)
            for column in range(self.columns)
        )

    def cell_center_m(self, cell: GridCell) -> Tuple[float, float]:
        """Return a cell center in grid-frame metres."""
        if not self.contains(cell):
            raise ValueError(f'cell outside board: {cell}')
        return (
            (cell.column + 0.5) * self.cell_size_m,
            (cell.row + 0.5) * self.cell_size_m,
        )


@dataclass(frozen=True)
class Cube:
    """One identified cube and its consistent grid/game positions."""

    cube_id: str
    kind: CubeKind
    cell: GridCell
    game_coordinate: GameCoordinate

    def __post_init__(self) -> None:
        """Require a stable non-empty cube identity."""
        if not isinstance(self.cube_id, str) or not self.cube_id:
            raise ValueError('cube_id must be a non-empty string')
        if not isinstance(self.kind, CubeKind):
            raise TypeError('kind must be CubeKind')
        if not isinstance(self.cell, GridCell):
            raise TypeError('cell must be GridCell')
        if not isinstance(self.game_coordinate, GameCoordinate):
            raise TypeError('game_coordinate must be GameCoordinate')


@dataclass(frozen=True)
class GameRound:
    """Complete immutable round generated once by the backend."""

    round_id: str
    random_seed: int
    mode: GameMode
    origin_cell: GridCell
    rotation: QuarterTurn
    handedness: Handedness
    cubes: Tuple[Cube, ...]
    green_cube_id: str
    answer_order: Tuple[str, ...]
    attempts: int
    beginner_target_cube_id: Optional[str] = None

    def __post_init__(self) -> None:
        """Protect the immutable round contract from inconsistent construction."""
        if not isinstance(self.mode, GameMode):
            raise TypeError('mode must be GameMode')
        if not isinstance(self.rotation, QuarterTurn):
            raise TypeError('rotation must be QuarterTurn')
        if not isinstance(self.handedness, Handedness):
            raise TypeError('handedness must be Handedness')
        if not self.round_id or isinstance(self.random_seed, bool):
            raise ValueError('round identity and integer seed are required')
        if (
            not isinstance(self.random_seed, int)
            or isinstance(self.attempts, bool)
            or not isinstance(self.attempts, int)
            or self.attempts < 1
        ):
            raise ValueError('round identity and positive attempts are required')
        ids = [cube.cube_id for cube in self.cubes]
        cells = [cube.cell for cube in self.cubes]
        coordinates = [cube.game_coordinate for cube in self.cubes]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError('round requires cubes with unique ids')
        if len(cells) != len(set(cells)) or self.origin_cell in cells:
            raise ValueError('cube cells must be unique and exclude the origin')
        if len(coordinates) != len(set(coordinates)):
            raise ValueError('cube game coordinates must be unique')
        green = [cube for cube in self.cubes if cube.kind is CubeKind.GREEN]
        if len(green) != 1 or green[0].cube_id != self.green_cube_id:
            raise ValueError('round requires exactly one identified green cube')
        if len(self.answer_order) != len(ids) or set(self.answer_order) != set(ids):
            raise ValueError('answer_order must contain every cube id exactly once')
        if self.mode is GameMode.BEGINNER:
            if self.beginner_target_cube_id not in ids:
                raise ValueError('Beginner round requires a valid target cube')
        elif self.beginner_target_cube_id is not None:
            raise ValueError('only Beginner rounds may define a target cube')

    def cube(self, cube_id: str) -> Cube:
        """Look up a cube by its stable identity."""
        for cube in self.cubes:
            if cube.cube_id == cube_id:
                return cube
        raise KeyError(cube_id)

    def is_correct(self, cube_id: str) -> bool:
        """Evaluate selection against mode-specific correctness."""
        if self.mode is GameMode.EASY:
            return cube_id == self.green_cube_id
        if self.mode is GameMode.BEGINNER:
            return cube_id == self.beginner_target_cube_id
        return cube_id == self.green_cube_id
