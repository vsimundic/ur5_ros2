"""Hardware-independent Robots and Cubes game domain."""

from .contracts import (
    ExecutionErrorCode,
    ExecutionOutcome,
    ExecutionResult,
    GameSnapshot,
    IntentResult,
    OperationRequest,
)
from .coordinates import game_to_grid, grid_to_game, transform_matrix
from .game_manager import GameManager
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
from .round_generator import RoundGenerationError, RoundGenerator
from .state_machine import GameState, GameStateMachine, PhysicalProgress

__all__ = [
    'Board', 'Cube', 'CubeKind', 'ExecutionErrorCode', 'ExecutionOutcome',
    'ExecutionResult', 'GameCoordinate', 'GameManager', 'GameMode', 'GameRound',
    'GameSnapshot', 'IntentResult', 'OperationRequest',
    'GameState', 'GameStateMachine', 'GridCell', 'Handedness', 'PhysicalProgress',
    'QuarterTurn',
    'RoundGenerationError', 'RoundGenerator', 'game_to_grid', 'grid_to_game',
    'transform_matrix',
]
