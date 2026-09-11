# Copyright 2026 UR5 ROS 2 maintainers

from csv import DictReader

import pytest

from robotiq_3f_calibration.sample_data import (
    append_csv_row,
    csv_fieldnames,
    JOINT_SPECS,
    MIDDLE_PIVOT_ORIGINS_M,
    PIVOT_SPECS,
    point_deltas,
    point_distance,
    read_csv_rows,
)


def test_joint_schema_matches_articulated_model():
    assert len(JOINT_SPECS) == 11
    assert len({spec.name for spec in JOINT_SPECS}) == 11
    assert JOINT_SPECS[0].name == 'robotiq_3f_finger_a_proximal_joint'
    assert JOINT_SPECS[-1].name == 'robotiq_3f_finger_c_distal_joint'
    assert all(spec.lower_deg < 0.0 < spec.upper_deg for spec in JOINT_SPECS)


def test_pivot_schema_has_xyz_for_each_middle_joint():
    assert len(PIVOT_SPECS) == 9
    assert len({spec.name for spec in PIVOT_SPECS}) == 9
    assert all(spec.lower_mm < 0.0 < spec.upper_mm for spec in PIVOT_SPECS)
    assert PIVOT_SPECS[0].name.endswith('finger_a_middle_joint_pivot_x_joint')
    assert PIVOT_SPECS[-1].name.endswith('finger_c_middle_joint_pivot_z_joint')
    assert set(MIDDLE_PIVOT_ORIGINS_M) == {'a', 'b', 'c'}
    assert all(len(origin) == 3 for origin in MIDDLE_PIVOT_ORIGINS_M.values())


def test_point_distance():
    assert point_distance((0.0, 0.0, 0.0), (0.03, 0.04, 0.0)) == pytest.approx(0.05)


def test_point_deltas_are_signed_b_minus_a():
    assert point_deltas(
        (0.01, 0.04, -0.02), (0.04, -0.01, 0.03)
    ) == pytest.approx((0.03, -0.05, 0.05))


def test_append_csv_row_creates_header_once(tmp_path):
    filename = tmp_path / 'samples' / 'calibration.csv'
    append_csv_row(filename, {'sample_id': 'basic_p000', 'actual_a': 6})
    append_csv_row(filename, {'sample_id': 'basic_p032', 'actual_a': 32})

    with filename.open(newline='', encoding='utf-8') as stream:
        rows = list(DictReader(stream))
    assert len(rows) == 2
    assert rows[0]['sample_id'] == 'basic_p000'
    assert rows[0]['actual_a'] == '6'
    assert rows[1]['sample_id'] == 'basic_p032'
    assert list(rows[0]) == csv_fieldnames()
    assert read_csv_rows(filename) == rows


def test_read_csv_rows_returns_empty_for_missing_file(tmp_path):
    assert read_csv_rows(tmp_path / 'missing.csv') == []
