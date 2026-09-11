# Copyright 2026 UR5 ROS 2 maintainers

"""Pure data helpers used by the Robotiq 3F calibration GUI."""

import csv
from dataclasses import dataclass
from math import sqrt
from pathlib import Path


MODE_NAMES = ('Basic', 'Pinch', 'Wide', 'Scissor')
MIDDLE_PIVOT_ORIGINS_M = {
    'a': (-0.069807455, -0.001425852, 0.00805),
    'b': (-0.069809366, -0.0013289835, 0.00804),
    'c': (-0.070573474, -0.0012468926, 0.00805),
}


@dataclass(frozen=True)
class JointSpec:
    """A movable description joint and its user-facing degree limits."""

    name: str
    label: str
    lower_deg: float
    upper_deg: float


@dataclass(frozen=True)
class PivotSpec:
    """A calibration-only middle-joint pivot offset in millimetres."""

    name: str
    label: str
    lower_mm: float = -30.0
    upper_mm: float = 30.0


JOINT_SPECS = (
    JointSpec('robotiq_3f_finger_a_proximal_joint', 'A proximal', -70.0, 70.0),
    JointSpec('robotiq_3f_finger_a_middle_joint', 'A middle', -90.0, 90.0),
    JointSpec('robotiq_3f_finger_a_distal_joint', 'A distal', -70.0, 70.0),
    JointSpec('robotiq_3f_finger_b_scissor_joint', 'B scissor', -17.0, 17.0),
    JointSpec('robotiq_3f_finger_b_proximal_joint', 'B proximal', -70.0, 70.0),
    JointSpec('robotiq_3f_finger_b_middle_joint', 'B middle', -90.0, 90.0),
    JointSpec('robotiq_3f_finger_b_distal_joint', 'B distal', -70.0, 70.0),
    JointSpec('robotiq_3f_finger_c_scissor_joint', 'C scissor', -17.0, 17.0),
    JointSpec('robotiq_3f_finger_c_proximal_joint', 'C proximal', -70.0, 70.0),
    JointSpec('robotiq_3f_finger_c_middle_joint', 'C middle', -90.0, 90.0),
    JointSpec('robotiq_3f_finger_c_distal_joint', 'C distal', -70.0, 70.0),
)

PIVOT_SPECS = tuple(
    PivotSpec(
        f'robotiq_3f_finger_{finger}_middle_joint_pivot_{axis}_joint',
        f'{finger.upper()} middle pivot {axis}',
    )
    for finger in ('a', 'b', 'c')
    for axis in ('x', 'y', 'z')
)


def point_distance(point_a, point_b):
    """Return Euclidean distance between two three-component iterables."""
    return sqrt(sum((a - b) ** 2 for a, b in zip(point_a, point_b)))


def point_deltas(point_a, point_b):
    """Return signed B-minus-A coordinate differences."""
    return tuple(b - a for a, b in zip(point_a, point_b))


def csv_fieldnames():
    """Return the stable on-disk sample schema."""
    fields = [
        'timestamp', 'sample_id', 'mode', 'mode_value',
        'requested_position', 'actual_a', 'actual_b', 'actual_c',
        'actual_scissor', 'status_connected', 'status_activated',
        'status_fault', 'status_motion', 'notes',
    ]
    fields.extend(spec.name + '_rad' for spec in JOINT_SPECS)
    fields.extend(spec.name + '_m' for spec in PIVOT_SPECS)
    fields.extend(spec.name + '_mm' for spec in PIVOT_SPECS)
    for finger in ('a', 'b', 'c'):
        fields.extend(
            f'finger_{finger}_middle_pivot_candidate_{axis}_{unit}'
            for unit in ('m', 'mm')
            for axis in ('x', 'y', 'z')
        )
    fields.extend([
        'measurement_label', 'measurement_frame',
        'point_a_x_m', 'point_a_y_m', 'point_a_z_m',
        'point_b_x_m', 'point_b_y_m', 'point_b_z_m',
        'delta_x_m', 'delta_y_m', 'delta_z_m',
        'delta_x_mm', 'delta_y_mm', 'delta_z_mm',
        'distance_m', 'distance_mm', 'real_distance_mm',
    ])
    return fields


def append_csv_row(filename, row):
    """Append one sample, writing a header when the file is new or empty."""
    path = Path(filename).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open('a', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=csv_fieldnames())
        if write_header:
            writer.writeheader()
        writer.writerow({field: row.get(field, '') for field in csv_fieldnames()})
    return path


def read_csv_rows(filename):
    """Read saved samples, returning an empty list for a missing/empty file."""
    path = Path(filename).expanduser()
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))
