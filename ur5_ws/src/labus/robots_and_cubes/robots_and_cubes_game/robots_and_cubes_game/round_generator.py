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
        """Return every legal origin for a mode under current configuration."""
        if mode is not GameMode.STANDARD:
            return self._board.cells()
        margin = self._settings.game.standard.central_origin_margin_cells
        return tuple(
            GridCell(column, row)
            for row in range(margin, self._board.rows - margin)
            for column in range(margin, self._board.columns - margin)
        )

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
        self, origin: GridCell, generator: random.Random
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
        origin: GridCell,
        rotation: QuarterTurn,
        handedness: Handedness,
        generator: random.Random,
    ) -> tuple[Cube, ...]:
        cells = list(cells)
        generator.shuffle(cells)
        cubes = []
        for index in range(self._settings.game.cubes.red_count):
            cell = cells[index]
            cubes.append(Cube(
                f'red_{index + 1}',
                CubeKind.RED,
                cell,
                grid_to_game(cell, origin, rotation, handedness),
            ))
        green_cell = cells[-1]
        cubes.append(Cube(
            'green_1',
            CubeKind.GREEN,
            green_cell,
            grid_to_game(green_cell, origin, rotation, handedness),
        ))
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
        best: tuple[int, GridCell, QuarterTurn, Handedness, tuple[Cube, ...]] | None = None

        for _ in range(self._settings.generation.maximum_attempts):
            origin = generator.choice(origins)
            rotation, handedness = self._orientation(mode, generator)
            cube_cells = self._choose_cube_cells(origin, generator)
            if cube_cells is None:
                continue
            cubes = self._make_cubes(
                cube_cells, origin, rotation, handedness, generator
            )
            signs = _signs(cubes)
            if not self._meets_required_signs(signs):
                continue
            score = len(signs) if self._settings.generation.favor_coordinate_sign_variety else 0
            candidate = (score, origin, rotation, handedness, cubes)
            if best is None or score > best[0]:
                best = candidate
            if score == 4 or not self._settings.generation.favor_coordinate_sign_variety:
                break

        if best is None:
            raise RoundGenerationError(
                'could not generate a valid layout with current settings'
            )
        _, origin, rotation, handedness, cubes = best
        answer_ids = [cube.cube_id for cube in cubes]
        generator.shuffle(answer_ids)
        beginner_target = generator.choice(answer_ids) if mode is GameMode.BEGINNER else None
        identity = '|'.join([
            str(actual_seed), mode.value, str(origin.column), str(origin.row),
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
            green_cube_id='green_1',
            answer_order=tuple(answer_ids),
            attempts=self._settings.game.attempts,
            beginner_target_cube_id=beginner_target,
        )
