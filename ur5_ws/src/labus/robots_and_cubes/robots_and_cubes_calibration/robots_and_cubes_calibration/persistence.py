"""Versioned, atomic persistence for accepted calibration and taught data."""

from dataclasses import asdict
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Mapping

import yaml

from .calibration_manager import AcceptedCalibration
from .geometry import GridTransform, Metrics

RUNTIME_SCHEMA_VERSION = 1


class RuntimeDataError(ValueError):
    """Stored runtime data is malformed or incompatible with current geometry."""


def save_atomic(path: Path, data: Mapping[str, Any]) -> None:
    """Serialize then replace one runtime YAML file without corrupting its predecessor."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with NamedTemporaryFile(
            'w', dir=path.parent, delete=False, encoding='utf-8'
        ) as stream:
            yaml.safe_dump(dict(data), stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
            temporary = stream.name
        os.replace(temporary, path)
    except (OSError, yaml.YAMLError) as error:
        if temporary:
            try:
                Path(temporary).unlink(missing_ok=True)
            except OSError:
                pass
        raise RuntimeDataError(f'cannot atomically save {path}: {error}') from error


def _load_mapping(path: Path) -> Mapping[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding='utf-8'))
    except (OSError, yaml.YAMLError) as error:
        raise RuntimeDataError(f'cannot load {path}: {error}') from error
    if not isinstance(value, dict):
        raise RuntimeDataError('runtime document must be a mapping')
    if value.get('schema_version') != RUNTIME_SCHEMA_VERSION:
        raise RuntimeDataError('unsupported runtime schema')
    return value


def _vector(value: object, name: str) -> tuple[float, float, float]:
    if not isinstance(value, list) or len(value) != 3:
        raise RuntimeDataError(f'{name} must contain three values')
    try:
        return tuple(float(item) for item in value)  # type: ignore[return-value]
    except (TypeError, ValueError) as error:
        raise RuntimeDataError(f'{name} must be numeric') from error


def calibration_to_data(calibration: AcceptedCalibration) -> dict[str, Any]:
    """Return the sole on-disk representation of an accepted calibration."""
    data = asdict(calibration)
    data['schema_version'] = RUNTIME_SCHEMA_VERSION
    return data


def calibration_from_data(
    data: Mapping[str, Any], geometry_revision: str, pen_transform_revision: str
) -> AcceptedCalibration:
    """Validate and reconstruct an accepted calibration compatible with this setup."""
    required = {
        'schema_version', 'calibration_id', 'revision', 'accepted_at', 'parent_frame',
        'child_frame', 'p0_m', 'px_m', 'py_m', 'pxy_m', 'transform', 'metrics',
        'fourth_point_error_m', 'geometry_revision', 'pen_transform_revision',
    }
    if set(data) != required:
        raise RuntimeDataError('calibration fields are missing or unknown')
    if data['schema_version'] != RUNTIME_SCHEMA_VERSION:
        raise RuntimeDataError('unsupported runtime schema')
    if data['geometry_revision'] != geometry_revision:
        raise RuntimeDataError('calibration geometry revision is incompatible')
    if data['pen_transform_revision'] != pen_transform_revision:
        raise RuntimeDataError('calibration pen transform revision is incompatible')
    if data['parent_frame'] != 'base_link' or data['child_frame'] != 'grid_frame':
        raise RuntimeDataError('calibration must define base_link -> grid_frame')
    transform_data = data['transform']
    metrics_data = data['metrics']
    if not isinstance(transform_data, dict) or not isinstance(metrics_data, dict):
        raise RuntimeDataError('calibration transform and metrics must be mappings')
    rotation = transform_data.get('rotation_matrix')
    if not isinstance(rotation, list) or len(rotation) != 3:
        raise RuntimeDataError('rotation_matrix must contain three axes')
    try:
        transform = GridTransform(
            parent_frame=str(transform_data['parent_frame']),
            child_frame=str(transform_data['child_frame']),
            translation_m=_vector(transform_data['translation_m'], 'translation_m'),
            rotation_matrix=tuple(
                _vector(axis, 'rotation axis') for axis in rotation
            ),  # type: ignore[arg-type]
        )
        metrics = Metrics(**{key: float(value) for key, value in metrics_data.items()})
        pxy_value = data['pxy_m']
        return AcceptedCalibration(
            calibration_id=str(data['calibration_id']),
            revision=int(data['revision']),
            accepted_at=str(data['accepted_at']),
            parent_frame='base_link',
            child_frame='grid_frame',
            p0_m=_vector(data['p0_m'], 'p0_m'),
            px_m=_vector(data['px_m'], 'px_m'),
            py_m=_vector(data['py_m'], 'py_m'),
            pxy_m=None if pxy_value is None else _vector(pxy_value, 'pxy_m'),
            transform=transform,
            metrics=metrics,
            fourth_point_error_m=(
                None if data['fourth_point_error_m'] is None
                else float(data['fourth_point_error_m'])
            ),
            geometry_revision=geometry_revision,
            pen_transform_revision=pen_transform_revision,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeDataError(f'malformed calibration data: {error}') from error


def save_calibration(path: Path, calibration: AcceptedCalibration) -> None:
    """Persist one already accepted calibration atomically."""
    save_atomic(path, calibration_to_data(calibration))


def load_calibration(
    path: Path, geometry_revision: str, pen_transform_revision: str
) -> AcceptedCalibration:
    """Load an accepted calibration only when its physical dependencies still match."""
    return calibration_from_data(
        _load_mapping(path), geometry_revision, pen_transform_revision
    )
