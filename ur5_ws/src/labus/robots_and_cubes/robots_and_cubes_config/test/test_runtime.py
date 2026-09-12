"""Tests for versioned generated-data schemas."""

from datetime import datetime, timezone

import pytest

from robots_and_cubes_config import CalibrationData, ConfigError, FrameTaggedPose


def _pose():
    return FrameTaggedPose('base_link', (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))


def test_calibration_schema_requires_explicit_base_link_pose():
    data = CalibrationData(
        schema_version=1,
        created_at=datetime.now(timezone.utc),
        task_reference_frame='base_link',
        p0_m=(0.0, 0.0, 0.0),
        px_m=(0.5, 0.0, 0.0),
        py_m=(0.0, 0.5, 0.0),
        grid_pose=_pose(),
        configuration_revision='config-1',
        quality={'angle_error_deg': 0.1},
    )
    assert data.task_reference_frame == 'base_link'


def test_calibration_schema_rejects_untagged_or_wrong_frame_data():
    with pytest.raises(ConfigError, match='task_reference_frame'):
        CalibrationData(
            1, datetime.now(timezone.utc), 'world', (0.0, 0.0, 0.0),
            (0.5, 0.0, 0.0), (0.0, 0.5, 0.0), _pose(), 'config-1', {},
        )
