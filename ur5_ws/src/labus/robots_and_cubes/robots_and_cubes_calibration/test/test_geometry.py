"""Calibration-geometry tests independent of ROS and robot hardware."""

import pytest

from robots_and_cubes_calibration.geometry import (
    calibrate,
    CalibrationGeometryError,
    fourth_point_error,
    pen_tip,
)


def test_axis_aligned_and_fourth_point():
    """An axis-aligned board produces the identity orientation."""
    transform, metric = calibrate(
        (1, 2, 3), (1.54, 2, 3), (1, 2.54, 3), .54, .54, .005, 1, .001
    )
    assert transform.rotation_matrix == ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.))
    assert metric.xy_angle_deg == 90
    assert fourth_point_error(transform, .54, .54, (1.54, 2.54, 3)) == 0


def test_tilted_board_is_right_handed():
    """A board tilted in Z still produces a right-handed normal."""
    transform, _ = calibrate(
        (0, 0, 0), (1, 0, 0), (0, 0, 1), 1, 1, .01, 1, .001
    )
    assert transform.rotation_matrix[2] == (0., -1., 0.)


def test_bad_geometry_rejected():
    """Duplicate and collinear points cannot define a board plane."""
    with pytest.raises(CalibrationGeometryError):
        calibrate((0, 0, 0), (0, 0, 0), (0, 1, 0), 1, 1, .1, 1, .001)
    with pytest.raises(CalibrationGeometryError):
        calibrate((0, 0, 0), (1, 0, 0), (2, 0, 0), 1, 1, .1, 1, .001)


def test_pen_offset_rotates_with_tool():
    """The pen-tip vector follows the full measured tool orientation."""
    assert pen_tip(
        (1, 2, 3), ((0, -1, 0), (1, 0, 0), (0, 0, 1)), (0, 0, .315)
    ) == (1, 2, 3.315)
    assert pen_tip(
        (1, 2, 3), ((0, 0, 1), (0, 1, 0), (-1, 0, 0)), (0, 0, .315)
    ) == (1.315, 2, 3)


def test_translated_rotated_and_noisy_board_is_orthonormal():
    """A translated, rotated board retains its expected axes under small noise."""
    transform, metrics = calibrate(
        (2, 3, 4), (2, 3.5405, 4), (1.46, 3, 4), .54, .54, .005, 1, .001
    )
    assert transform.translation_m == (2, 3, 4)
    assert transform.rotation_matrix[0] == (0.0, 1.0, 0.0)
    assert transform.rotation_matrix[1] == (-1.0, 0.0, 0.0)
    assert transform.rotation_matrix[2] == (0.0, 0.0, 1.0)
    assert metrics.x_length_error == pytest.approx(.0005)


@pytest.mark.parametrize(
    ('px', 'py'),
    [((.55, 0, 0), (0, .54, 0)), ((.54, 0, 0), (0, .55, 0)),
     ((.54, 0, 0), (.1, .54, 0))],
)
def test_measurement_failures_are_rejected(px, py):
    """X length, Y length, and angle tolerance violations are rejected."""
    with pytest.raises(CalibrationGeometryError, match='tolerance'):
        calibrate((0, 0, 0), px, py, .54, .54, .005, 1, .001)
