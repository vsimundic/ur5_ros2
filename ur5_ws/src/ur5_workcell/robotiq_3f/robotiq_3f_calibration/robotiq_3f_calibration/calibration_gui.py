# Copyright 2026 UR5 ROS 2 maintainers

"""Qt and ROS application for fitting the articulated Robotiq 3F model."""

from datetime import datetime, timezone
from math import pi
import sys

from geometry_msgs.msg import Point, PointStamped
from python_qt_binding.QtCore import Qt, QTimer
from python_qt_binding.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rclpy.utilities import remove_ros_args
from robotiq_3f_interfaces.msg import Robotiq3FStatus
from sensor_msgs.msg import JointState
from visualization_msgs.msg import Marker, MarkerArray

from .sample_data import (
    append_csv_row,
    JOINT_SPECS,
    MIDDLE_PIVOT_ORIGINS_M,
    MODE_NAMES,
    PIVOT_SPECS,
    point_deltas,
    point_distance,
    read_csv_rows,
)


DEG_TO_RAD = pi / 180.0


class CalibrationNode(Node):
    """Bridge GUI state to JointState, status, and RViz point messages."""

    def __init__(self):
        super().__init__('robotiq_3f_calibration')
        self.declare_parameter(
            'output_file',
            '/workspaces/ur5_ros2/gripper_calibration/gripper_samples.csv',
        )
        self.declare_parameter('status_topic', '/robotiq_3f/status')
        self.declare_parameter('clicked_point_topic', '/clicked_point')
        self.output_file = self.get_parameter('output_file').value
        status_topic = self.get_parameter('status_topic').value
        clicked_point_topic = self.get_parameter('clicked_point_topic').value

        self.status_callback = None
        self.point_callback = None
        self.joint_positions = [0.0] * len(JOINT_SPECS)
        self.pivot_positions = [0.0] * len(PIVOT_SPECS)
        self.joint_publisher = self.create_publisher(
            JointState, '/joint_states', 10
        )
        marker_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.marker_publisher = self.create_publisher(
            MarkerArray,
            '/robotiq_3f/calibration/measurement_markers',
            marker_qos,
        )
        self.pivot_marker_publisher = self.create_publisher(
            MarkerArray,
            '/robotiq_3f/calibration/pivot_markers',
            marker_qos,
        )
        self.create_subscription(
            Robotiq3FStatus, status_topic, self._receive_status, 10
        )
        self.create_subscription(
            PointStamped, clicked_point_topic, self._receive_point, 10
        )
        self.create_timer(0.05, self._publish_joints)
        self.create_timer(0.5, self._publish_pivot_markers)

    def _receive_status(self, message):
        if self.status_callback is not None:
            self.status_callback(message)

    def _receive_point(self, message):
        if self.point_callback is not None:
            self.point_callback(message)

    def _publish_joints(self):
        message = JointState()
        message.header.stamp = self.get_clock().now().to_msg()
        message.name = (
            [spec.name for spec in JOINT_SPECS] +
            [spec.name for spec in PIVOT_SPECS]
        )
        message.position = self.joint_positions + self.pivot_positions
        self.joint_publisher.publish(message)

    def _publish_pivot_markers(self):
        """Show each adjustable middle-joint center in its moving TF frame."""
        array = MarkerArray()
        colors = {
            'a': (0.95, 0.2, 0.2),
            'b': (0.2, 0.9, 0.25),
            'c': (0.2, 0.45, 1.0),
        }
        for index, finger in enumerate(('a', 'b', 'c')):
            frame = (
                f'robotiq_3f_finger_{finger}_middle_joint_pivot_z_link'
            )
            sphere = Marker()
            sphere.header.frame_id = frame
            sphere.header.stamp = self.get_clock().now().to_msg()
            sphere.ns = 'pivot_centers'
            sphere.id = index * 2
            sphere.type = Marker.SPHERE
            sphere.action = Marker.ADD
            sphere.pose.orientation.w = 1.0
            sphere.scale.x = sphere.scale.y = sphere.scale.z = 0.007
            sphere.color.r, sphere.color.g, sphere.color.b = colors[finger]
            sphere.color.a = 0.9
            sphere.frame_locked = True
            array.markers.append(sphere)

            label = Marker()
            label.header.frame_id = frame
            label.header.stamp = sphere.header.stamp
            label.ns = 'pivot_centers'
            label.id = index * 2 + 1
            label.type = Marker.TEXT_VIEW_FACING
            label.action = Marker.ADD
            label.pose.position.z = 0.012
            label.pose.orientation.w = 1.0
            label.scale.z = 0.009
            label.color.r = label.color.g = label.color.b = 1.0
            label.color.a = 1.0
            label.text = f'{finger.upper()} middle pivot'
            label.frame_locked = True
            array.markers.append(label)
        self.pivot_marker_publisher.publish(array)

    def publish_measurement(self, point_a, point_b, distance, deltas):
        """Draw the selected endpoints, line, and distance label in RViz."""
        frame_id = point_a.header.frame_id
        stamp = self.get_clock().now().to_msg()
        array = MarkerArray()

        for marker_id, source, color in (
            (0, point_a.point, (0.1, 0.9, 0.2)),
            (1, point_b.point, (0.95, 0.25, 0.1)),
        ):
            marker = Marker()
            marker.header.frame_id = frame_id
            marker.header.stamp = stamp
            marker.ns = 'measurement'
            marker.id = marker_id
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD
            marker.pose.position = source
            marker.pose.orientation.w = 1.0
            marker.scale.x = marker.scale.y = marker.scale.z = 0.006
            marker.color.r, marker.color.g, marker.color.b = color
            marker.color.a = 1.0
            array.markers.append(marker)

        line = Marker()
        line.header.frame_id = frame_id
        line.header.stamp = stamp
        line.ns = 'measurement'
        line.id = 2
        line.type = Marker.LINE_LIST
        line.action = Marker.ADD
        line.scale.x = 0.002
        line.color.r = 1.0
        line.color.g = 0.85
        line.color.b = 0.1
        line.color.a = 1.0
        line.points = [point_a.point, point_b.point]
        array.markers.append(line)

        label = Marker()
        label.header.frame_id = frame_id
        label.header.stamp = stamp
        label.ns = 'measurement'
        label.id = 3
        label.type = Marker.TEXT_VIEW_FACING
        label.action = Marker.ADD
        label.pose.position = Point(
            x=(point_a.point.x + point_b.point.x) / 2.0,
            y=(point_a.point.y + point_b.point.y) / 2.0,
            z=(point_a.point.z + point_b.point.z) / 2.0 + 0.01,
        )
        label.pose.orientation.w = 1.0
        label.scale.z = 0.01
        label.color.r = label.color.g = label.color.b = 1.0
        label.color.a = 1.0
        label.text = (
            f'{distance * 1000.0:.2f} mm '
            f'(dx={deltas[0] * 1000.0:+.2f}, '
            f'dy={deltas[1] * 1000.0:+.2f}, '
            f'dz={deltas[2] * 1000.0:+.2f} mm)'
        )
        array.markers.append(label)
        self.marker_publisher.publish(array)

    def clear_measurement(self):
        """Remove all calibration measurement markers from RViz."""
        marker = Marker()
        marker.action = Marker.DELETEALL
        self.marker_publisher.publish(MarkerArray(markers=[marker]))


class CalibrationWindow(QMainWindow):
    """Calibration controls, metadata editor, and CSV recorder."""

    def __init__(self, node):
        super().__init__()
        self.node = node
        self.latest_status = None
        self.point_a = None
        self.point_b = None
        self.distance_m = None
        self.deltas_m = None
        self.joint_sliders = []
        self.joint_spins = []
        self.pivot_sliders = []
        self.pivot_spins = []
        self.pivot_candidate_labels = []
        self.saved_rows = []

        self.setWindowTitle('Robotiq 3F model calibration')
        self.resize(720, 900)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        contents = QWidget()
        layout = QVBoxLayout(contents)
        layout.addWidget(self._create_instructions())
        layout.addWidget(self._create_sample_group())
        layout.addWidget(self._create_joint_group())
        layout.addWidget(self._create_pivot_group())
        layout.addWidget(self._create_measurement_group())
        layout.addWidget(self._create_record_group())
        layout.addStretch(1)
        scroll.setWidget(contents)
        self.setCentralWidget(scroll)

        self.node.status_callback = self.receive_status
        self.node.point_callback = self.receive_point
        self.statusBar().showMessage(
            'Visualization only: sliders never command the physical gripper.'
        )

    def _create_instructions(self):
        label = QLabel(
            '<b>Visualization only.</b> Adjust model joints, describe the real '
            'pose, and record it. In RViz select <b>Publish Point</b>, then '
            'click endpoints A and B to capture a distance.'
        )
        label.setWordWrap(True)
        return label

    def _create_sample_group(self):
        group = QGroupBox('Real gripper sample')
        layout = QGridLayout(group)
        self.sample_id = QLineEdit()
        self.mode = QComboBox()
        self.mode.addItems(MODE_NAMES)
        self.requested_position = self._byte_spin()
        self.actual_spins = [self._byte_spin() for _ in range(4)]
        self.actual_spins[3].setValue(137)
        self.follow_status = QCheckBox('Follow live /robotiq_3f/status')
        self.follow_status.setChecked(True)
        self.status_label = QLabel('No live status received')
        self.status_label.setWordWrap(True)
        copy_button = QPushButton('Copy latest status')
        copy_button.clicked.connect(self.copy_latest_status)

        layout.addWidget(QLabel('Sample ID'), 0, 0)
        layout.addWidget(self.sample_id, 0, 1, 1, 3)
        layout.addWidget(QLabel('Mode'), 1, 0)
        layout.addWidget(self.mode, 1, 1)
        layout.addWidget(QLabel('Requested mode position'), 1, 2)
        layout.addWidget(self.requested_position, 1, 3)
        for column, (label, spin) in enumerate(zip(
                ('Actual A', 'Actual B', 'Actual C', 'Actual S'),
                self.actual_spins)):
            layout.addWidget(QLabel(label), 2, column)
            layout.addWidget(spin, 3, column)
        layout.addWidget(self.follow_status, 4, 0, 1, 3)
        layout.addWidget(copy_button, 4, 3)
        layout.addWidget(self.status_label, 5, 0, 1, 4)
        return group

    @staticmethod
    def _byte_spin():
        spin = QSpinBox()
        spin.setRange(0, 255)
        return spin

    def _create_joint_group(self):
        group = QGroupBox('Model joint angles')
        layout = QGridLayout(group)
        layout.addWidget(QLabel('Joint'), 0, 0)
        layout.addWidget(QLabel('Drag'), 0, 1)
        layout.addWidget(QLabel('Angle'), 0, 2)
        for row, spec in enumerate(JOINT_SPECS, start=1):
            slider = QSlider(Qt.Horizontal)
            slider.setRange(
                round(spec.lower_deg * 100), round(spec.upper_deg * 100)
            )
            spin = QDoubleSpinBox()
            spin.setRange(spec.lower_deg, spec.upper_deg)
            spin.setDecimals(2)
            spin.setSingleStep(0.25)
            spin.setSuffix(' deg')
            slider.valueChanged.connect(
                lambda value, target=spin: target.setValue(value / 100.0)
            )
            spin.valueChanged.connect(
                lambda value, target=slider: target.setValue(round(value * 100))
            )
            spin.valueChanged.connect(self.update_joint_positions)
            self.joint_sliders.append(slider)
            self.joint_spins.append(spin)
            layout.addWidget(QLabel(spec.label), row, 0)
            layout.addWidget(slider, row, 1)
            layout.addWidget(spin, row, 2)

        buttons = QHBoxLayout()
        zero_button = QPushButton('Reset model to Basic/open zero')
        zero_button.clicked.connect(self.reset_joints)
        copy_button = QPushButton('Copy A bend to B and C')
        copy_button.clicked.connect(self.copy_a_to_outer_fingers)
        buttons.addWidget(zero_button)
        buttons.addWidget(copy_button)
        layout.addLayout(buttons, len(JOINT_SPECS) + 1, 0, 1, 3)
        return group

    def _create_measurement_group(self):
        group = QGroupBox('Point-to-point measurement')
        layout = QFormLayout(group)
        self.measurement_label = QLineEdit()
        self.point_a_label = QLabel('Not selected')
        self.point_b_label = QLabel('Not selected')
        self.visual_distance = QLabel('Not available')
        self.axis_distances = QLabel('Not available')
        self.real_distance = QDoubleSpinBox()
        self.real_distance.setRange(0.0, 10000.0)
        self.real_distance.setDecimals(3)
        self.real_distance.setSuffix(' mm')
        clear_button = QPushButton('Clear selected points')
        clear_button.clicked.connect(self.clear_points)
        layout.addRow('Measurement name', self.measurement_label)
        layout.addRow('Point A', self.point_a_label)
        layout.addRow('Point B', self.point_b_label)
        layout.addRow('Visualized distance', self.visual_distance)
        layout.addRow('Signed B - A components', self.axis_distances)
        layout.addRow('Real measured distance', self.real_distance)
        layout.addRow(clear_button)
        return group

    def _create_pivot_group(self):
        group = QGroupBox(
            'Middle-joint pivot offsets in proximal-link coordinates'
        )
        layout = QGridLayout(group)
        explanation = QLabel(
            'Zero preserves the current assembled pose. Change an offset, '
            'then bend that finger middle joint to see the new rotation center.'
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation, 0, 0, 1, 3)
        layout.addWidget(QLabel('Pivot coordinate'), 1, 0)
        layout.addWidget(QLabel('Drag'), 1, 1)
        layout.addWidget(QLabel('Offset'), 1, 2)
        for row, spec in enumerate(PIVOT_SPECS, start=2):
            slider = QSlider(Qt.Horizontal)
            slider.setRange(
                round(spec.lower_mm * 100), round(spec.upper_mm * 100)
            )
            spin = QDoubleSpinBox()
            spin.setRange(spec.lower_mm, spec.upper_mm)
            spin.setDecimals(2)
            spin.setSingleStep(0.10)
            spin.setSuffix(' mm')
            slider.valueChanged.connect(
                lambda value, target=spin: target.setValue(value / 100.0)
            )
            spin.valueChanged.connect(
                lambda value, target=slider: target.setValue(round(value * 100))
            )
            spin.valueChanged.connect(self.update_pivot_positions)
            self.pivot_sliders.append(slider)
            self.pivot_spins.append(spin)
            layout.addWidget(QLabel(spec.label), row, 0)
            layout.addWidget(slider, row, 1)
            layout.addWidget(spin, row, 2)

        candidate_start = len(PIVOT_SPECS) + 2
        for index, finger in enumerate(('a', 'b', 'c')):
            candidate = QLabel()
            self.pivot_candidate_labels.append(candidate)
            layout.addWidget(
                QLabel(f'{finger.upper()} candidate xacro xyz'),
                candidate_start + index, 0,
            )
            layout.addWidget(candidate, candidate_start + index, 1, 1, 2)

        buttons = QHBoxLayout()
        reset_button = QPushButton('Reset all pivot offsets')
        reset_button.clicked.connect(self.reset_pivots)
        copy_button = QPushButton('Copy A pivot offset to B and C')
        copy_button.clicked.connect(self.copy_a_pivot_to_outer_fingers)
        buttons.addWidget(reset_button)
        buttons.addWidget(copy_button)
        layout.addLayout(buttons, candidate_start + 3, 0, 1, 3)
        self.update_pivot_positions()
        return group

    def _create_record_group(self):
        group = QGroupBox('Record')
        layout = QFormLayout(group)
        self.output_file = QLineEdit(self.node.output_file)
        browse = QPushButton('Browse')
        browse.clicked.connect(self.browse_output)
        file_row = QHBoxLayout()
        file_row.addWidget(self.output_file)
        file_row.addWidget(browse)
        self.notes = QLineEdit()
        self.saved_configurations = QComboBox()
        refresh = QPushButton('Refresh saved configurations')
        refresh.clicked.connect(self.reload_saved_configurations)
        load = QPushButton('Load selected')
        load.clicked.connect(self.load_selected_configuration)
        duplicate = QPushButton('Duplicate as new sample')
        duplicate.clicked.connect(self.duplicate_selected_configuration)
        saved_buttons = QHBoxLayout()
        saved_buttons.addWidget(refresh)
        saved_buttons.addWidget(load)
        saved_buttons.addWidget(duplicate)
        record = QPushButton('Record sample to CSV')
        record.clicked.connect(self.record_sample)
        layout.addRow('CSV file', file_row)
        layout.addRow('Notes / photo filenames', self.notes)
        layout.addRow('Saved configuration', self.saved_configurations)
        layout.addRow(saved_buttons)
        layout.addRow(record)
        self.reload_saved_configurations()
        return group

    def reload_saved_configurations(self):
        """Reload the configuration selector from the current CSV file."""
        try:
            self.saved_rows = read_csv_rows(self.output_file.text())
        except (OSError, ValueError) as exception:
            QMessageBox.warning(
                self, 'Could not read saved configurations', str(exception)
            )
            return
        self.saved_configurations.clear()
        for index, row in enumerate(self.saved_rows):
            sample_id = row.get('sample_id') or f'row_{index + 1}'
            mode = row.get('mode', '')
            requested = row.get('requested_position', '')
            timestamp = row.get('timestamp', '')
            self.saved_configurations.addItem(
                f'{sample_id} | {mode} p{requested} | {timestamp}', index
            )
        self.statusBar().showMessage(
            f'Found {len(self.saved_rows)} saved configuration(s).', 5000
        )

    @staticmethod
    def _row_float(row, name, default=0.0):
        value = row.get(name, '')
        return default if value in ('', None) else float(value)

    @staticmethod
    def _row_int(row, name, default=0):
        value = row.get(name, '')
        return default if value in ('', None) else int(float(value))

    def load_selected_configuration(self):
        """Restore every recorded field into the visualization and form."""
        index = self.saved_configurations.currentData()
        if index is None or not self.saved_rows:
            self.statusBar().showMessage('No saved configuration is selected.')
            return
        row = self.saved_rows[index]
        try:
            self._apply_saved_row(row)
        except (TypeError, ValueError) as exception:
            QMessageBox.warning(
                self, 'Could not load saved configuration', str(exception)
            )
            return
        self.statusBar().showMessage(
            f"Loaded {row.get('sample_id', 'saved configuration')}. "
            'Only the visualization was moved.',
            10000,
        )

    def duplicate_selected_configuration(self):
        """Restore a saved row and assign a unique copy sample ID."""
        index = self.saved_configurations.currentData()
        if index is None or not self.saved_rows:
            self.statusBar().showMessage('No saved configuration is selected.')
            return
        row = self.saved_rows[index]
        try:
            self._apply_saved_row(row)
        except (TypeError, ValueError) as exception:
            QMessageBox.warning(
                self, 'Could not duplicate saved configuration', str(exception)
            )
            return
        base = (row.get('sample_id') or 'sample') + '_copy'
        existing = {saved.get('sample_id', '') for saved in self.saved_rows}
        candidate = base
        suffix = 2
        while candidate in existing:
            candidate = f'{base}_{suffix}'
            suffix += 1
        self.sample_id.setText(candidate)
        self.statusBar().showMessage(
            f'Loaded configuration as {candidate}; press Record to save it.',
            10000,
        )

    def _apply_saved_row(self, row):
        """Apply one CSV row without issuing any hardware command."""
        self.follow_status.setChecked(False)
        self.sample_id.setText(row.get('sample_id', ''))
        mode_value = self._row_int(row, 'mode_value')
        if 0 <= mode_value < self.mode.count():
            self.mode.setCurrentIndex(mode_value)
        self.requested_position.setValue(
            self._row_int(row, 'requested_position')
        )
        for spin, field in zip(
                self.actual_spins,
                ('actual_a', 'actual_b', 'actual_c', 'actual_scissor')):
            spin.setValue(self._row_int(row, field))
        for spin, spec in zip(self.joint_spins, JOINT_SPECS):
            radians = self._row_float(row, spec.name + '_rad')
            spin.setValue(radians / DEG_TO_RAD)
        for spin, spec in zip(self.pivot_spins, PIVOT_SPECS):
            metres = self._row_float(row, spec.name + '_m')
            spin.setValue(metres * 1000.0)
        self.notes.setText(row.get('notes', ''))
        self.measurement_label.setText(row.get('measurement_label', ''))
        self.real_distance.setValue(
            self._row_float(row, 'real_distance_mm')
        )
        self._restore_saved_measurement(row)

    def _restore_saved_measurement(self, row):
        """Restore stored endpoints and republish their RViz annotation."""
        fields = (
            'point_a_x_m', 'point_a_y_m', 'point_a_z_m',
            'point_b_x_m', 'point_b_y_m', 'point_b_z_m',
        )
        if any(row.get(field, '') in ('', None) for field in fields):
            self.clear_points()
            return
        frame = row.get('measurement_frame') or 'world'
        point_a = PointStamped()
        point_a.header.frame_id = frame
        point_a.point.x = self._row_float(row, 'point_a_x_m')
        point_a.point.y = self._row_float(row, 'point_a_y_m')
        point_a.point.z = self._row_float(row, 'point_a_z_m')
        point_b = PointStamped()
        point_b.header.frame_id = frame
        point_b.point.x = self._row_float(row, 'point_b_x_m')
        point_b.point.y = self._row_float(row, 'point_b_y_m')
        point_b.point.z = self._row_float(row, 'point_b_z_m')
        self.receive_point(point_a)
        self.receive_point(point_b)

    def update_joint_positions(self):
        """Copy user-selected degree values into the ROS joint message."""
        self.node.joint_positions = [
            spin.value() * DEG_TO_RAD for spin in self.joint_spins
        ]

    def reset_joints(self):
        """Restore the exact fixed-model reference pose."""
        for spin in self.joint_spins:
            spin.setValue(0.0)

    def update_pivot_positions(self):
        """Publish millimetre GUI offsets as metre prismatic positions."""
        self.node.pivot_positions = [
            spin.value() / 1000.0 for spin in self.pivot_spins
        ]
        for index, finger in enumerate(('a', 'b', 'c')):
            origin = MIDDLE_PIVOT_ORIGINS_M[finger]
            offsets = self.node.pivot_positions[index * 3:index * 3 + 3]
            candidate = tuple(
                base + offset for base, offset in zip(origin, offsets)
            )
            self.pivot_candidate_labels[index].setText(
                f'{candidate[0]:+.6f} {candidate[1]:+.6f} '
                f'{candidate[2]:+.6f} m'
            )

    def reset_pivots(self):
        """Restore all rotation centers to their current xacro origins."""
        for spin in self.pivot_spins:
            spin.setValue(0.0)

    def copy_a_pivot_to_outer_fingers(self):
        """Copy Finger A's relative pivot offset to Fingers B and C."""
        values = [spin.value() for spin in self.pivot_spins[:3]]
        for start in (3, 6):
            for axis, value in enumerate(values):
                self.pivot_spins[start + axis].setValue(value)

    def copy_a_to_outer_fingers(self):
        """Use Finger A bend angles for Fingers B and C."""
        proximal = self.joint_spins[0].value()
        middle = self.joint_spins[1].value()
        distal = self.joint_spins[2].value()
        for start in (4, 8):
            self.joint_spins[start].setValue(proximal)
            self.joint_spins[start + 1].setValue(middle)
            self.joint_spins[start + 2].setValue(distal)

    def receive_status(self, status):
        """Store status and optionally mirror its fields into the form."""
        self.latest_status = status
        self.status_label.setText(
            f'connected={status.connected}, activated={status.activated}, '
            f'mode={status.mode}, motion={status.motion_status}, '
            f'fault={status.fault_status}'
        )
        if self.follow_status.isChecked():
            self.copy_latest_status()

    def copy_latest_status(self):
        """Copy the most recently received raw feedback into editable fields."""
        if self.latest_status is None:
            self.statusBar().showMessage('No gripper status has been received.')
            return
        status = self.latest_status
        if 0 <= status.mode < self.mode.count():
            self.mode.setCurrentIndex(status.mode)
        values = (
            status.actual_position_a,
            status.actual_position_b,
            status.actual_position_c,
            status.actual_position_scissor,
        )
        for spin, value in zip(self.actual_spins, values):
            spin.setValue(value)
        self.requested_position.setValue(status.requested_position_a)

    @staticmethod
    def _format_point(message):
        point = message.point
        return (
            f'{message.header.frame_id}: '
            f'({point.x:.5f}, {point.y:.5f}, {point.z:.5f}) m'
        )

    def receive_point(self, point):
        """Treat consecutive RViz point clicks as measurement endpoints."""
        if self.point_a is None or self.point_b is not None:
            self.point_a = point
            self.point_b = None
            self.distance_m = None
            self.deltas_m = None
            self.point_a_label.setText(self._format_point(point))
            self.point_b_label.setText('Select Point B')
            self.visual_distance.setText('Waiting for Point B')
            self.axis_distances.setText('Waiting for Point B')
            self.node.clear_measurement()
            return
        if point.header.frame_id != self.point_a.header.frame_id:
            self.statusBar().showMessage(
                'Points must be selected in the same RViz fixed frame.'
            )
            return
        self.point_b = point
        coordinates_a = (
            self.point_a.point.x,
            self.point_a.point.y,
            self.point_a.point.z,
        )
        coordinates_b = (point.point.x, point.point.y, point.point.z)
        self.distance_m = point_distance(coordinates_a, coordinates_b)
        self.deltas_m = point_deltas(coordinates_a, coordinates_b)
        self.point_b_label.setText(self._format_point(point))
        self.visual_distance.setText(f'{self.distance_m * 1000.0:.3f} mm')
        self.axis_distances.setText(
            f'dx={self.deltas_m[0] * 1000.0:+.3f} mm, '
            f'dy={self.deltas_m[1] * 1000.0:+.3f} mm, '
            f'dz={self.deltas_m[2] * 1000.0:+.3f} mm'
        )
        self.node.publish_measurement(
            self.point_a, self.point_b, self.distance_m, self.deltas_m
        )

    def clear_points(self):
        """Reset selected measurement endpoints and their RViz markers."""
        self.point_a = self.point_b = None
        self.distance_m = None
        self.deltas_m = None
        self.point_a_label.setText('Not selected')
        self.point_b_label.setText('Not selected')
        self.visual_distance.setText('Not available')
        self.axis_distances.setText('Not available')
        self.node.clear_measurement()

    def browse_output(self):
        """Choose the destination CSV file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, 'Calibration CSV', self.output_file.text(), 'CSV (*.csv)'
        )
        if filename:
            self.output_file.setText(filename)
            self.reload_saved_configurations()

    def record_sample(self):
        """Append the current reviewed inputs to the stable CSV schema."""
        sample_id = self.sample_id.text().strip()
        if not sample_id:
            sample_id = (
                f'{self.mode.currentText().lower()}_'
                f'p{self.requested_position.value():03d}'
            )
            self.sample_id.setText(sample_id)
        status = self.latest_status
        row = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'sample_id': sample_id,
            'mode': self.mode.currentText(),
            'mode_value': self.mode.currentIndex(),
            'requested_position': self.requested_position.value(),
            'actual_a': self.actual_spins[0].value(),
            'actual_b': self.actual_spins[1].value(),
            'actual_c': self.actual_spins[2].value(),
            'actual_scissor': self.actual_spins[3].value(),
            'status_connected': '' if status is None else status.connected,
            'status_activated': '' if status is None else status.activated,
            'status_fault': '' if status is None else status.fault_status,
            'status_motion': '' if status is None else status.motion_status,
            'notes': self.notes.text().strip(),
            'measurement_label': self.measurement_label.text().strip(),
            'real_distance_mm': self.real_distance.value(),
        }
        for spec, position in zip(JOINT_SPECS, self.node.joint_positions):
            row[spec.name + '_rad'] = f'{position:.9f}'
        for spec, position in zip(PIVOT_SPECS, self.node.pivot_positions):
            row[spec.name + '_m'] = f'{position:.9f}'
            row[spec.name + '_mm'] = f'{position * 1000.0:.3f}'
        for index, finger in enumerate(('a', 'b', 'c')):
            origin = MIDDLE_PIVOT_ORIGINS_M[finger]
            offsets = self.node.pivot_positions[index * 3:index * 3 + 3]
            for axis, base, offset in zip(('x', 'y', 'z'), origin, offsets):
                candidate = base + offset
                row[f'finger_{finger}_middle_pivot_candidate_{axis}_m'] = (
                    f'{candidate:.9f}'
                )
                row[f'finger_{finger}_middle_pivot_candidate_{axis}_mm'] = (
                    f'{candidate * 1000.0:.3f}'
                )
        if self.point_a is not None:
            row.update({
                'measurement_frame': self.point_a.header.frame_id,
                'point_a_x_m': self.point_a.point.x,
                'point_a_y_m': self.point_a.point.y,
                'point_a_z_m': self.point_a.point.z,
            })
        if self.point_b is not None:
            row.update({
                'point_b_x_m': self.point_b.point.x,
                'point_b_y_m': self.point_b.point.y,
                'point_b_z_m': self.point_b.point.z,
                'delta_x_m': self.deltas_m[0],
                'delta_y_m': self.deltas_m[1],
                'delta_z_m': self.deltas_m[2],
                'delta_x_mm': self.deltas_m[0] * 1000.0,
                'delta_y_mm': self.deltas_m[1] * 1000.0,
                'delta_z_mm': self.deltas_m[2] * 1000.0,
                'distance_m': self.distance_m,
                'distance_mm': self.distance_m * 1000.0,
            })
        try:
            path = append_csv_row(self.output_file.text(), row)
        except (OSError, ValueError) as exception:
            QMessageBox.critical(self, 'Could not record sample', str(exception))
            return
        self.reload_saved_configurations()
        self.saved_configurations.setCurrentIndex(
            self.saved_configurations.count() - 1
        )
        self.statusBar().showMessage(f'Recorded {sample_id} to {path}', 10000)


def main(args=None):
    """Run Qt and service ROS callbacks from a non-blocking timer."""
    rclpy.init(args=args)
    node = CalibrationNode()
    application = QApplication(remove_ros_args(args=sys.argv))
    window = CalibrationWindow(node)
    timer = QTimer()

    def spin_ros():
        if rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.0)
        else:
            application.quit()

    timer.timeout.connect(spin_ros)
    timer.start(10)
    window.show()
    try:
        exit_code = application.exec_()
    finally:
        timer.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
