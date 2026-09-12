"""Pure, right-handed board calibration geometry expressed in ``base_link``."""

from dataclasses import dataclass
from math import acos, degrees, isfinite, sqrt
from typing import Tuple

Vector = Tuple[float, float, float]
Matrix = Tuple[Vector, Vector, Vector]


class CalibrationGeometryError(ValueError):
    """Raised when captured geometry cannot define an acceptable board frame."""


@dataclass(frozen=True)
class Metrics:
    """Measurements retained with an accepted three-point calibration."""

    measured_x_length: float
    measured_y_length: float
    x_length_error: float
    y_length_error: float
    xy_angle_deg: float
    angle_error_deg: float
    orthogonality_error: float


@dataclass(frozen=True)
class GridTransform:
    """An explicit ``base_link -> grid_frame`` rigid transform."""

    parent_frame: str
    child_frame: str
    translation_m: Vector
    rotation_matrix: Matrix


def vector_add(first: Vector, second: Vector) -> Vector:
    """Return the component-wise sum of two vectors."""
    return tuple(a + b for a, b in zip(first, second))  # type: ignore[return-value]


def vector_subtract(first: Vector, second: Vector) -> Vector:
    """Return the component-wise difference of two vectors."""
    return tuple(a - b for a, b in zip(first, second))  # type: ignore[return-value]


def vector_scale(vector: Vector, scalar: float) -> Vector:
    """Return a vector scaled by ``scalar``."""
    return tuple(value * scalar for value in vector)  # type: ignore[return-value]


def dot(first: Vector, second: Vector) -> float:
    """Return the dot product."""
    return sum(a * b for a, b in zip(first, second))


def cross(first: Vector, second: Vector) -> Vector:
    """Return the right-handed cross product."""
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def norm(vector: Vector) -> float:
    """Return a vector's Euclidean length."""
    return sqrt(dot(vector, vector))


def unit(vector: Vector, epsilon: float) -> Vector:
    """Normalize a finite, non-degenerate vector."""
    length = norm(vector)
    if len(vector) != 3 or not all(isfinite(value) for value in vector) or length <= epsilon:
        raise CalibrationGeometryError('degenerate calibration vector')
    return vector_scale(vector, 1.0 / length)


def pen_tip(
    tool_translation: Vector, tool_rotation: Matrix, pen_offset: Vector
) -> Vector:
    """Transform the local pen vector using the complete measured tool rotation."""
    return vector_add(
        tool_translation,
        tuple(dot(axis, pen_offset) for axis in tool_rotation),  # type: ignore[arg-type]
    )


def calibrate(
    p0: Vector,
    px: Vector,
    py: Vector,
    width: float,
    height: float,
    side_limit: float,
    angle_limit: float,
    epsilon: float,
) -> tuple[GridTransform, Metrics]:
    """
    Construct ``base_link -> grid_frame`` from P0, PX, and PY.

    The raw Y measurement supplies the normal direction, then Gram--Schmidt
    orthonormalization supplies an exact right-handed frame.  The measurement
    angle is retained as a validation metric rather than hidden by that step.
    """
    x_vector = vector_subtract(px, p0)
    y_vector = vector_subtract(py, p0)
    measured_x_length = norm(x_vector)
    measured_y_length = norm(y_vector)
    x_axis = unit(x_vector, epsilon)
    raw_y_axis = unit(y_vector, epsilon)
    z_axis = unit(cross(x_axis, y_vector), epsilon)
    y_axis = cross(z_axis, x_axis)
    cosine = max(-1.0, min(1.0, dot(x_axis, raw_y_axis)))
    angle = degrees(acos(cosine))
    metrics = Metrics(
        measured_x_length=measured_x_length,
        measured_y_length=measured_y_length,
        x_length_error=abs(measured_x_length - width),
        y_length_error=abs(measured_y_length - height),
        xy_angle_deg=angle,
        angle_error_deg=abs(angle - 90.0),
        orthogonality_error=abs(dot(x_axis, y_axis)),
    )
    if (
        metrics.x_length_error > side_limit
        or metrics.y_length_error > side_limit
        or metrics.angle_error_deg > angle_limit
    ):
        raise CalibrationGeometryError('calibration geometry exceeds configured tolerance')
    return GridTransform('base_link', 'grid_frame', p0, (x_axis, y_axis, z_axis)), metrics


def fourth_point_error(
    transform: GridTransform, width: float, height: float, actual: Vector
) -> float:
    """Return PXY's distance from its predicted location; never alter the frame."""
    expected = vector_add(
        transform.translation_m,
        vector_add(
            vector_scale(transform.rotation_matrix[0], width),
            vector_scale(transform.rotation_matrix[1], height),
        ),
    )
    return norm(vector_subtract(actual, expected))
