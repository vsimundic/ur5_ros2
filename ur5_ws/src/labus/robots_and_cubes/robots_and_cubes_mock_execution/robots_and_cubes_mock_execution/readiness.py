"""Explicitly synthetic mock fixtures; they are not commissioning records."""

from dataclasses import dataclass

from robots_and_cubes_config.models import UserSettings


@dataclass(frozen=True)
class SyntheticMockReadiness:
    """Application readiness for mock only, never proof of physical readiness."""

    settings: UserSettings
    disabled_cells: frozenset[tuple[int, int]] = frozenset()

    synthetic: bool = True
    calibration_id: str = 'SYNTHETIC_MOCK_CALIBRATION_ONLY'
    home_id: str = 'SYNTHETIC_MOCK_HOME_ONLY'
    safe_id: str = 'SYNTHETIC_MOCK_SAFE_ONLY'
    green_destination_id: str = 'SYNTHETIC_MOCK_GREEN_REWARD_ONLY'
    red_destination_id: str = 'SYNTHETIC_MOCK_RED_CAPACITY_ONLY'

    @property
    def real_hardware_ready(self) -> bool:
        """Prevent mock fixtures from satisfying any real readiness gate."""
        return False

    def cell_enabled(self, column: int, row: int) -> bool:
        """Return mock board availability, not physical reachability."""
        return (
            0 <= column < self.settings.board.columns
            and 0 <= row < self.settings.board.rows
            and (column, row) not in self.disabled_cells
        )

    def preflight(self) -> tuple[bool, str]:
        """Validate only synthetic fixture consistency before child input unlocks."""
        return (True, '')

    def validate_goal(self, goal) -> tuple[bool, str]:
        """Validate request identity, synthetic source availability, and destination policy."""
        if not all((goal.request_id, goal.operation_id, goal.round_id, goal.cube_id)):
            return False, 'mock goal identity is incomplete'
        if not self.cell_enabled(goal.grid_column, goal.grid_row):
            return False, 'mock source cell is unavailable'
        if goal.destination_id not in ('green_reward', 'beginner_demo', 'red_drop'):
            return False, 'mock destination is unsupported'
        if goal.destination_policy not in ('configured_destination', 'BEGINNER_CORRECT'):
            return False, 'mock destination policy is unsupported'
        return True, ''
