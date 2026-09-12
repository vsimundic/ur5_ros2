"""Synthetic fixtures must be useful to mock and useless to real readiness."""

from robots_and_cubes_mock_execution.readiness import SyntheticMockReadiness


def test_synthetic_readiness_enables_mock_cells_but_never_real_hardware(settings):
    readiness = SyntheticMockReadiness(settings, frozenset({(0, 0)}))
    assert readiness.synthetic
    assert readiness.cell_enabled(1, 1)
    assert not readiness.cell_enabled(0, 0)
    assert not readiness.cell_enabled(99, 99)
    assert not readiness.real_hardware_ready
    assert readiness.calibration_id.startswith('SYNTHETIC_MOCK_')
