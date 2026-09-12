"""Future-UI readiness gates; these deliberately do not authorize robot motion."""

from dataclasses import dataclass


@dataclass(frozen=True)
class OperatorReadiness:
    """Calibration and teaching facts needed before later commissioning gates."""

    grid_calibration_valid: bool
    home_taught: bool
    safe_taught: bool
    green_reward_taught: bool
    red_drop_capacity_taught: bool
    real_motion_ready: bool = False


def operator_readiness(calibration: object, teaching: object) -> OperatorReadiness:
    """Combine Phase 4 facts without representing later motion gates as complete."""
    taught = teaching.readiness()
    return OperatorReadiness(
        grid_calibration_valid=calibration.status().active_valid,
        home_taught=bool(taught['home_taught']),
        safe_taught=bool(taught['safe_taught']),
        green_reward_taught=bool(taught['green_reward_taught']),
        red_drop_capacity_taught=bool(taught['red_drop_capacity_taught']),
    )
