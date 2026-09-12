"""Command-free capture and acceptance of operator-taught positions."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from time import time
from typing import Callable, Dict, Mapping, Optional, Tuple

from .persistence import RUNTIME_SCHEMA_VERSION, RuntimeDataError, save_atomic

ARM_JOINTS = (
    'shoulder_pan_joint',
    'shoulder_lift_joint',
    'elbow_joint',
    'wrist_1_joint',
    'wrist_2_joint',
    'wrist_3_joint',
)
JOINT_POSITION_NAMES = {'home', 'safe'}
DESTINATION_TYPES = {'reward', 'red_slot', 'red_bin', 'beginner_demo'}


@dataclass(frozen=True)
class MeasuredJointState:
    """An actual arm state from a joint-state provider, never a command echo."""

    names: Tuple[str, ...]
    positions_rad: Tuple[float, ...]
    stamp_seconds: float
    source: str = 'measured_joint_state'


@dataclass(frozen=True)
class MeasuredCartesianPose:
    """An actual Cartesian pose with an explicit reference frame."""

    frame_id: str
    translation_m: Tuple[float, float, float]
    rotation_xyzw: Tuple[float, float, float, float]
    stamp_seconds: float
    source: str = 'measured_tf'


@dataclass(frozen=True)
class TaughtPosition:
    """A candidate or accepted position with provenance and compatibility revision."""

    name: str
    kind: str
    captured_at: str
    source: str
    configuration_revision: str
    data: dict


class TeachingManager:
    """Capture candidates first; only explicit acceptance mutates active teaching data."""

    def __init__(
        self,
        configuration_revision: str,
        maximum_age_seconds: float,
        beginner_correct_destination: str,
        clock: Callable[[], float] = time,
        event_logger: object | None = None,
    ) -> None:
        if beginner_correct_destination not in {'green_reward', 'beginner_demo'}:
            raise ValueError('unsupported Beginner correct-destination policy')
        self.configuration_revision = configuration_revision
        self.maximum_age_seconds = maximum_age_seconds
        self.beginner_correct_destination = beginner_correct_destination
        self.clock = clock
        self.event_logger = event_logger
        self.accepted: Dict[str, TaughtPosition] = {}
        self.candidates: Dict[str, TaughtPosition] = {}

    def _event(self, event_type: str, payload: dict) -> None:
        if self.event_logger is not None:
            try:
                self.event_logger.write(event_type, 0, None, None, payload)
            except (AttributeError, OSError, ValueError):
                pass

    def _fresh(self, stamp_seconds: float) -> None:
        if self.clock() - stamp_seconds > self.maximum_age_seconds:
            raise ValueError('measured state is stale')

    def capture_joints(self, name: str, measured: MeasuredJointState) -> TaughtPosition:
        """Capture home or safe from an actual fresh UR joint state."""
        if name not in JOINT_POSITION_NAMES:
            raise ValueError('only home and safe are taught as joint states')
        self._fresh(measured.stamp_seconds)
        if set(measured.names) != set(ARM_JOINTS) or len(measured.names) != len(ARM_JOINTS):
            raise ValueError('joint state must contain exactly the six UR arm joints')
        position_map = dict(zip(measured.names, measured.positions_rad))
        if len(position_map) != len(ARM_JOINTS):
            raise ValueError('joint state names must be unique and complete')
        candidate = TaughtPosition(
            name=name,
            kind='joint_state',
            captured_at=datetime.now(timezone.utc).isoformat(),
            source=measured.source,
            configuration_revision=self.configuration_revision,
            data={
                'joint_names': list(ARM_JOINTS),
                'joint_positions_rad': [position_map[joint] for joint in ARM_JOINTS],
                'measured_stamp_seconds': measured.stamp_seconds,
            },
        )
        self.candidates[name] = candidate
        self._event('taught_position_captured', {'name': name, 'kind': candidate.kind})
        return candidate

    def capture_destination(
        self,
        name: str,
        destination_type: str,
        release_pose: MeasuredCartesianPose,
        approach_offset_m: Optional[Tuple[float, float, float]] = None,
        retreat_offset_m: Optional[Tuple[float, float, float]] = None,
    ) -> TaughtPosition:
        """Capture one cartesian destination in ``base_link`` without planning it."""
        if destination_type not in DESTINATION_TYPES:
            raise ValueError('unknown destination type')
        if name == 'green_reward' and destination_type != 'reward':
            raise ValueError('green_reward must use the reward destination type')
        if name.startswith('red_') and destination_type not in {'red_slot', 'red_bin'}:
            raise ValueError('red destinations must be an explicit slot or bin')
        self._fresh(release_pose.stamp_seconds)
        if release_pose.frame_id != 'base_link':
            raise ValueError('cartesian destinations must be expressed in base_link')
        data = {
            'frame_id': 'base_link',
            'release_pose': {
                'translation_m': list(release_pose.translation_m),
                'rotation_xyzw': list(release_pose.rotation_xyzw),
            },
            'measured_stamp_seconds': release_pose.stamp_seconds,
            'destination_type': destination_type,
        }
        if approach_offset_m is not None:
            data['approach_offset_m'] = list(approach_offset_m)
        if retreat_offset_m is not None:
            data['retreat_offset_m'] = list(retreat_offset_m)
        if name == 'beginner_demo':
            data['logical_policy'] = 'BEGINNER_CORRECT'
        candidate = TaughtPosition(
            name=name,
            kind='cartesian_destination',
            captured_at=datetime.now(timezone.utc).isoformat(),
            source=release_pose.source,
            configuration_revision=self.configuration_revision,
            data=data,
        )
        self.candidates[name] = candidate
        self._event('taught_position_captured', {'name': name, 'kind': candidate.kind})
        return candidate

    def accept(
        self,
        name: str,
        persist: Callable[[TaughtPosition, dict], None] | None = None,
    ) -> TaughtPosition:
        """Replace exactly one accepted teaching value with its inspected candidate."""
        if name not in self.candidates:
            raise ValueError('no taught-position candidate exists')
        value = self.candidates[name]
        pending = dict(self.accepted)
        pending[name] = value
        if persist is not None:
            persist(value, self.to_data(pending))
        self.candidates.pop(name)
        self.accepted[name] = value
        self._event('taught_position_accepted', {'name': name})
        return value

    def cancel(self, name: str) -> None:
        """Discard a candidate without changing an accepted taught position."""
        self.candidates.pop(name, None)

    def delete(self, name: str) -> None:
        """Delete an accepted taught position explicitly."""
        if self.accepted.pop(name, None) is not None:
            self._event('taught_position_deleted', {'name': name})

    def list_accepted(self) -> Tuple[TaughtPosition, ...]:
        """Return accepted values in deterministic name order."""
        return tuple(self.accepted[name] for name in sorted(self.accepted))

    def readiness(self) -> dict[str, bool | str]:
        """Expose teaching gates without declaring a robot system ready."""
        destinations = self.accepted
        red_slots = [
            item for item in destinations.values()
            if item.data.get('destination_type') == 'red_slot'
        ]
        red_bins = [
            item for item in destinations.values()
            if item.data.get('destination_type') == 'red_bin'
        ]
        return {
            'home_taught': 'home' in destinations,
            'safe_taught': 'safe' in destinations,
            'green_reward_taught': 'green_reward' in destinations,
            'red_drop_capacity_taught': bool(red_bins) or bool(red_slots),
            'beginner_correct_destination': self.beginner_correct_destination,
        }

    def to_data(self, positions: Optional[Mapping[str, TaughtPosition]] = None) -> dict:
        """Create a versioned persistence document containing accepted values only."""
        return {
            'schema_version': RUNTIME_SCHEMA_VERSION,
            'configuration_revision': self.configuration_revision,
            'beginner_correct_destination': self.beginner_correct_destination,
            'positions': {
                name: asdict(value) for name, value in (positions or self.accepted).items()
            },
        }

    def save(self, path: object) -> None:
        """Persist accepted teaching data atomically."""
        save_atomic(path, self.to_data())

    def load(self, path: object) -> None:
        """Replace in-memory accepted data only after full compatibility validation."""
        try:
            import yaml
            value = yaml.safe_load(path.read_text(encoding='utf-8'))
        except (OSError, yaml.YAMLError) as error:
            raise RuntimeDataError(f'cannot load taught positions: {error}') from error
        if not isinstance(value, dict) or value.get('schema_version') != RUNTIME_SCHEMA_VERSION:
            raise RuntimeDataError('unsupported taught-position schema')
        if value.get('configuration_revision') != self.configuration_revision:
            raise RuntimeDataError('taught positions are incompatible with current configuration')
        if value.get('beginner_correct_destination') != self.beginner_correct_destination:
            raise RuntimeDataError('Beginner destination policy changed')
        positions = value.get('positions')
        if not isinstance(positions, dict):
            raise RuntimeDataError('taught positions must be a mapping')
        loaded: Dict[str, TaughtPosition] = {}
        try:
            for name, record in positions.items():
                if not isinstance(record, dict) or record.get('name') != name:
                    raise RuntimeDataError('malformed taught position')
                position = TaughtPosition(**record)
                if position.configuration_revision != self.configuration_revision:
                    raise RuntimeDataError(
                        'taught position configuration revision is incompatible'
                    )
                if position.kind == 'joint_state':
                    if (
                        position.data.get('joint_names') != list(ARM_JOINTS)
                        or len(position.data.get('joint_positions_rad', [])) != len(ARM_JOINTS)
                    ):
                        raise RuntimeDataError('malformed taught joint state')
                elif position.kind == 'cartesian_destination':
                    if (
                        position.data.get('frame_id') != 'base_link'
                        or position.data.get('destination_type') not in DESTINATION_TYPES
                    ):
                        raise RuntimeDataError('malformed taught cartesian destination')
                else:
                    raise RuntimeDataError('unknown taught position kind')
                loaded[name] = position
        except (TypeError, ValueError) as error:
            raise RuntimeDataError(f'malformed taught position: {error}') from error
        self.accepted = loaded
