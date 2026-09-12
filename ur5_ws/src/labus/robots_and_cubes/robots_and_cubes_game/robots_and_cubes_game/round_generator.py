"""Seeded, bounded generation of valid Robots and Cubes rounds."""

from hashlib import sha256
import random
import secrets
from typing import Iterable, Sequence

from robots_and_cubes_config.models import UserSettings

from .coordinates import grid_to_game
from .models import (
    Board,
    Cube,
    CubeKind,
    GameCoordinate,
    GameMode,
    GameRound,
    GridCell,
    Handedness,
    QuarterTurn,
)


class RoundGenerationError(RuntimeError):
    """No round satisfies the configured constraints within the bound."""


def _distance(first: GridCell, second: GridCell) -> int:
    """Return Manhattan distance in cells."""
    return abs(first.column - second.column) + abs(first.row - second.row)


def _signs(cubes: Iterable[Cube]) -> set[str]:
    result = set()
    for cube in cubes:
        coordinate = cube.game_coordinate
        if coordinate.x > 0:
            result.add('+x')
        if coordinate.x < 0:
            result.add('-x')
        if coordinate.y > 0:
            result.add('+y')
        if coordinate.y < 0:
            result.add('-y')
    return result


class RoundGenerator:
    """Generate immutable rounds without ROS or hardware dependencies."""

    def __init__(self, settings: UserSettings):
        """Create a generator from already validated settings."""
        self._settings = settings
        self._board = Board(
            settings.board.rows,
            settings.board.columns,
            settings.board.cell_size_m,
        )

    def origin_cells(self, mode: GameMode) -> Sequence[GridCell]:
        """Return legal origins for the selected educational mode."""
        if mode in (GameMode.EASY, GameMode.BEGINNER):
            return ()
        if mode is GameMode.SPATIAL:
            spatial = self._settings.game.spatial
            return (GridCell(spatial.origin_column, spatial.origin_row),)
        if mode is GameMode.STANDARD:
            margin = self._settings.game.standard.central_origin_margin_cells
            return tuple(
                GridCell(column, row)
                for row in range(margin, self._board.rows - margin)
                for column in range(margin, self._board.columns - margin)
            )
        return self._board.cells()

    def _orientation(
        self, mode: GameMode, generator: random.Random
    ) -> tuple[QuarterTurn, Handedness]:
        if mode is not GameMode.CHALLENGE:
            return QuarterTurn.DEG_0, Handedness.RIGHT
        rotation = QuarterTurn(
            generator.choice(self._settings.game.challenge.rotations_deg)
        )
        handednesses = [Handedness.RIGHT]
        if self._settings.game.challenge.enable_left_handed:
            handednesses.append(Handedness.LEFT)
        return rotation, generator.choice(handednesses)

    def _choose_cube_cells(
        self, origin: GridCell | None, generator: random.Random
    ) -> tuple[GridCell, ...] | None:
        candidates = [cell for cell in self._board.cells() if cell != origin]
        generator.shuffle(candidates)
        chosen: list[GridCell] = []
        required_distance = self._settings.generation.minimum_cell_distance
        for candidate in candidates:
            if all(_distance(candidate, existing) >= required_distance for existing in chosen):
                chosen.append(candidate)
                if len(chosen) == self._settings.game.cubes.total:
                    return tuple(chosen)
        return None

    def _make_cubes(
        self,
        cells: Sequence[GridCell],
        origin: GridCell | None,
        rotation: QuarterTurn,
        handedness: Handedness,
        generator: random.Random,
    ) -> tuple[Cube, ...]:
        cells = list(cells)
        generator.shuffle(cells)
        cubes = []
        kinds = (
            CubeKind.RED, CubeKind.GREEN, CubeKind.BLUE,
            CubeKind.BLACK, CubeKind.WHITE,
        )
        for index, kind in enumerate(kinds):
            cell = cells[index]
            coordinate = (
                GameCoordinate(cell.column, cell.row)
                if origin is None
                else grid_to_game(cell, origin, rotation, handedness)
            )
            cubes.append(Cube(f'{kind.value}_1', kind, cell, coordinate))
        return tuple(cubes)

    def _meets_required_signs(self, signs: set[str]) -> bool:
        generation = self._settings.generation
        requirements = {
            '+x': generation.require_positive_x,
            '-x': generation.require_negative_x,
            '+y': generation.require_positive_y,
            '-y': generation.require_negative_y,
        }
        return all(not required or sign in signs for sign, required in requirements.items())

    def generate(self, mode: GameMode, seed: int | None = None) -> GameRound:
        """Generate one reproducible round, or fail after the configured bound."""
        if mode.value not in self._settings.game.enabled_modes:
            raise RoundGenerationError(f'mode is disabled: {mode.value}')
        actual_seed = secrets.randbits(63) if seed is None else seed
        if isinstance(actual_seed, bool) or not isinstance(actual_seed, int):
            raise TypeError('seed must be an integer or None')
        generator = random.Random(actual_seed)
        origins = self.origin_cells(mode)
        coordinate_round = mode in (
            GameMode.SPATIAL, GameMode.STANDARD, GameMode.CHALLENGE,
        )
        best: tuple[
            int, GridCell | None, QuarterTurn, Handedness, tuple[Cube, ...]
        ] | None = None

        for _ in range(self._settings.generation.maximum_attempts):
            origin = generator.choice(origins) if coordinate_round else None
            rotation, handedness = self._orientation(mode, generator)
            cube_cells = self._choose_cube_cells(origin, generator)
            if cube_cells is None:
                continue
            cubes = self._make_cubes(
                cube_cells, origin, rotation, handedness, generator
            )
            signs = _signs(cubes) if coordinate_round else set()
            if coordinate_round and not self._meets_required_signs(signs):
                continue
            score = (
                len(signs)
                if coordinate_round and self._settings.generation.favor_coordinate_sign_variety
                else 0
            )
            candidate = (score, origin, rotation, handedness, cubes)
            if best is None or score > best[0]:
                best = candidate
            if (
                score == 4
                or not coordinate_round
                or not self._settings.generation.favor_coordinate_sign_variety
            ):
                break

        if best is None:
            raise RoundGenerationError(
                'could not generate a valid layout with current settings'
            )
        _, origin, rotation, handedness, cubes = best
        answer_ids = [cube.cube_id for cube in cubes]
        generator.shuffle(answer_ids)
        target_id = (
            'green_1'
            if mode is GameMode.STANDARD
            else generator.choice(answer_ids)
        )
        identity = '|'.join([
            str(actual_seed), mode.value,
            '' if origin is None else str(origin.column),
            '' if origin is None else str(origin.row),
            str(int(rotation)), handedness.value,
            *(f'{cube.cube_id}:{cube.cell.column},{cube.cell.row}' for cube in cubes),
        ])
        round_id = sha256(identity.encode('utf-8')).hexdigest()[:16]
        return GameRound(
            round_id=round_id,
            random_seed=actual_seed,
            mode=mode,
            origin_cell=origin,
            rotation=rotation,
            handedness=handedness,
            cubes=cubes,
            target_cube_id=target_id,
            answer_order=tuple(answer_ids),
            attempts=self._settings.game.attempts,
        )
