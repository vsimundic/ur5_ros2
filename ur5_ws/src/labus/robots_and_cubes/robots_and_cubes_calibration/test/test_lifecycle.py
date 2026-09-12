"""Lifecycle, persistence, teaching, and command-free adapter tests."""

from pathlib import Path

import pytest

from robots_and_cubes_calibration.calibration_manager import (
    CalibrationGeometryError,
    CalibrationManager,
    CalibrationState,
    MeasuredToolPose,
)
from robots_and_cubes_calibration.persistence import (
    load_calibration,
    RuntimeDataError,
    save_calibration,
)
from robots_and_cubes_calibration.ros_adapter import CalibrationRosAdapter
from robots_and_cubes_calibration.teaching_manager import (
    ARM_JOINTS,
    MeasuredCartesianPose,
    MeasuredJointState,
    TeachingManager,
)
from robots_and_cubes_config import load_user_settings


CONFIG = Path(__file__).parents[2] / 'config' / 'user_settings.yaml'
IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def settings():
    """Load the real project defaults for every test."""
    return load_user_settings(CONFIG)


def pose(x, y, z, stamp=10.0):
    """Make a fresh fake measured base_link-to-tool0 transform."""
    return MeasuredToolPose((x, y, z), IDENTITY, stamp)


def calibrated(manager):
    """Capture one exact 6x6 board after the pen's fixed Z offset."""
    manager.start()
    manager.capture('P0', pose(0.0, 0.0, 0.0))
    manager.capture('PX', pose(0.54, 0.0, 0.0))
    manager.capture('PY', pose(0.0, 0.54, 0.0))
    manager.validate()
    return manager.accept()


def calibration_manager(clock=lambda: 10.0):
    return CalibrationManager(
        settings(), (0.0, 0.0, 0.315), 'geometry-a', 'pen-a', clock
    )


def test_lifecycle_cancel_and_invalid_draft_preserve_active_calibration():
    manager = calibration_manager()
    original = calibrated(manager)
    manager.start()
    manager.capture('P0', pose(1.0, 0.0, 0.0))
    manager.cancel()
    assert manager.accepted == original
    assert manager.state is CalibrationState.ACCEPTED

    manager.start()
    manager.capture('P0', pose(0.0, 0.0, 0.0))
    manager.capture('PX', pose(0.0, 0.0, 0.0))
    manager.capture('PY', pose(0.0, 0.54, 0.0))
    with pytest.raises(CalibrationGeometryError):
        manager.validate()
    assert manager.state is CalibrationState.INVALID
    assert manager.accepted == original


def test_accept_replaces_only_after_persistence_succeeds():
    manager = calibration_manager()
    original = calibrated(manager)
    manager.start()
    manager.capture('P0', pose(1.0, 0.0, 0.0))
    manager.capture('PX', pose(1.54, 0.0, 0.0))
    manager.capture('PY', pose(1.0, 0.54, 0.0))
    candidate = manager.validate()
    with pytest.raises(RuntimeError):
        manager.accept(lambda _: (_ for _ in ()).throw(RuntimeError('disk failure')))
    assert manager.accepted == original
    assert manager.state is CalibrationState.VALIDATED
    accepted = manager.accept()
    assert accepted.calibration_id == candidate.calibration_id
    assert accepted.calibration_id != original.calibration_id


def test_optional_pxy_validates_without_changing_transform():
    manager = calibration_manager()
    manager.start()
    manager.capture('P0', pose(0.0, 0.0, 0.0))
    manager.capture('PX', pose(0.54, 0.0, 0.0))
    manager.capture('PY', pose(0.0, 0.54, 0.0))
    manager.capture('PXY', pose(0.54, 0.54, 0.0))
    candidate = manager.validate()
    assert candidate.fourth_point_error_m == pytest.approx(0.0)
    assert candidate.transform.translation_m == (0.0, 0.0, 0.315)


def test_pxy_and_stale_capture_are_rejected():
    manager = calibration_manager()
    manager.start()
    with pytest.raises(CalibrationGeometryError, match='stale'):
        manager.capture('P0', pose(0.0, 0.0, 0.0, stamp=1.0))
    manager.capture('P0', pose(0.0, 0.0, 0.0))
    manager.capture('PX', pose(0.54, 0.0, 0.0))
    manager.capture('PY', pose(0.0, 0.54, 0.0))
    manager.capture('PXY', pose(0.0, 0.0, 0.0))
    with pytest.raises(CalibrationGeometryError, match='fourth point'):
        manager.validate()


def test_calibration_round_trip_and_incompatibility(tmp_path):
    path = tmp_path / 'calibration.yaml'
    accepted = calibrated(calibration_manager())
    save_calibration(path, accepted)
    assert load_calibration(path, 'geometry-a', 'pen-a') == accepted
    with pytest.raises(RuntimeDataError, match='geometry revision'):
        load_calibration(path, 'geometry-b', 'pen-a')
    with pytest.raises(RuntimeDataError, match='pen transform'):
        load_calibration(path, 'geometry-a', 'pen-b')
    path.write_text('schema_version: 99\n', encoding='utf-8')
    with pytest.raises(RuntimeDataError):
        load_calibration(path, 'geometry-a', 'pen-a')
    path.write_text(': invalid yaml', encoding='utf-8')
    with pytest.raises(RuntimeDataError):
        load_calibration(path, 'geometry-a', 'pen-a')


def joint_state(stamp=10.0):
    return MeasuredJointState(ARM_JOINTS, (0.1, 0.2, 0.3, 0.4, 0.5, 0.6), stamp)


def cartesian(stamp=10.0, frame='base_link'):
    return MeasuredCartesianPose(frame, (1.0, 2.0, 3.0), (0.0, 0.0, 0.0, 1.0), stamp)


def teaching_manager(clock=lambda: 10.0):
    return TeachingManager('geometry-a', 0.5, 'green_reward', clock)


def test_teaching_capture_accept_cancel_red_models_and_policy(tmp_path):
    teaching = teaching_manager()
    teaching.capture_joints('home', joint_state())
    teaching.accept('home')
    teaching.capture_joints('safe', joint_state())
    teaching.cancel('safe')
    assert 'safe' not in teaching.accepted
    teaching.capture_destination('green_reward', 'reward', cartesian())
    teaching.accept('green_reward')
    teaching.capture_destination('red_1', 'red_slot', cartesian())
    teaching.accept('red_1')
    teaching.capture_destination('red_bin', 'red_bin', cartesian())
    teaching.accept('red_bin')
    assert teaching.readiness()['red_drop_capacity_taught']
    assert teaching.readiness()['beginner_correct_destination'] == 'green_reward'
    taught_path = tmp_path / 'taught_poses.yaml'
    teaching.save(taught_path)
    reloaded = teaching_manager()
    reloaded.load(taught_path)
    assert set(reloaded.accepted) == {'home', 'green_reward', 'red_1', 'red_bin'}
    taught_path.write_text('schema_version: 1\npositions: []\n', encoding='utf-8')
    with pytest.raises(RuntimeDataError):
        reloaded.load(taught_path)


def test_teaching_rejects_stale_or_wrong_frame_and_preserves_accepted():
    teaching = teaching_manager()
    with pytest.raises(ValueError, match='stale'):
        teaching.capture_joints('home', joint_state(1.0))
    with pytest.raises(ValueError, match='base_link'):
        teaching.capture_destination('green_reward', 'reward', cartesian(frame='world'))
    teaching.capture_joints('home', joint_state())
    teaching.accept('home')
    teaching.capture_joints('home', joint_state())
    teaching.cancel('home')
    assert teaching.accepted['home'].kind == 'joint_state'


class Publisher:
    """Test-only fixed TF publisher; no command endpoint exists."""

    def __init__(self):
        self.transforms = []

    def publish_grid_transform(self, transform):
        self.transforms.append(transform)


def test_adapter_reads_fake_state_persists_and_publishes_only_accepted_grid(tmp_path):
    manager = calibration_manager()
    teaching = teaching_manager()
    points = iter([pose(0.0, 0.0, 0.0), pose(0.54, 0.0, 0.0), pose(0.0, 0.54, 0.0)])
    publisher = Publisher()
    adapter = CalibrationRosAdapter(
        manager, teaching, lambda: next(points), joint_state, cartesian, publisher,
        tmp_path / 'calibration.yaml', tmp_path / 'taught_poses.yaml',
    )
    adapter.start_calibration('start')
    for name in ('P0', 'PX', 'PY'):
        adapter.capture_calibration_point(name, name)
    adapter.validate_calibration('validate')
    accepted = adapter.accept_calibration('accept')
    assert accepted.parent_frame == 'base_link'
    assert len(publisher.transforms) == 1
    assert (tmp_path / 'calibration.yaml').exists()
