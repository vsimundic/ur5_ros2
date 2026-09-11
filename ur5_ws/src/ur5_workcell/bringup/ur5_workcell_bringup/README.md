# UR5 workcell bringup

This package connects the authoritative workcell description to the official
Universal Robots ROS 2 driver. It does not contain robot geometry or hardware
driver implementations.

The real-hardware entry point is `launch/hardware.launch.py`. The verified cell
addresses are installed in `config/hardware.yaml` and remain overridable launch
arguments. The selected arm motion controller is loaded and activated. The
external FT streamer and verified gripper stack start as part of
normal hardware bringup. Gripper writes are enabled for explicit calls, but
launch and reconnect send no activation or motion command. A non-commanding
gripper joint-state mapper publishes the reviewed Basic/open reference until
valid status arrives. The L515 camera remains an optional subsystem and is
enabled in the current cell defaults; pass `launch_camera:=false` to suppress
it. MoveIt and task nodes are not launched.

```bash
ros2 launch ur5_workcell_bringup hardware.launch.py robot_ip:=<robot-ip>
```

For an offline controller/description check, use mock hardware and a dummy IP:

```bash
ros2 launch ur5_workcell_bringup hardware.launch.py \
  robot_ip:=127.0.0.1 use_mock_hardware:=true
```

## RealSense L515

Enable the wrist-mounted camera explicitly:

```bash
ros2 launch ur5_workcell_bringup hardware.launch.py \
  launch_camera:=true
```

The current verified profiles are 640 x 480 color and depth at 30 Hz, with
aligned depth enabled. Point-cloud publication is disabled by default and can
be requested with `camera_pointcloud:=true`. Physical testing showed that this
L515 rejects the legacy 640 x 480 depth-at-15-Hz request. The `/camera` namespace
preserves the legacy `/camera/color/image_raw`,
`/camera/aligned_depth_to_color/image_raw`, and
`/camera/color/camera_info` paths. The authoritative description publishes
`tool0 -> camera_link`; the RealSense wrapper uses `camera_link` as its root
and publishes only downstream sensor/optical transforms. See the repository
README for the physical validation commands.

For isolated camera testing without the rest of workcell bringup, use:

```bash
ros2 launch realsense2_camera rs_launch.py \
  camera_namespace:=/camera \
  camera_name:=camera \
  device_type:=L515 \
  depth_module.profile:=640x480x30 \
  rgb_camera.profile:=640x480x30 \
  enable_depth:=true \
  enable_color:=true \
  align_depth.enable:=true \
  pointcloud.enable:=false \
  publish_tf:=true \
  base_frame_id:=link
```

Do not run the standalone and integrated camera launches simultaneously.

## External Robotiq FT sensor

The external sensor stream starts with normal hardware bringup:

```bash
ros2 launch ur5_workcell_bringup hardware.launch.py \
  robot_ip:=<robot-ip>
```

Startup zeroing is disabled. The node publishes immediately using a zero
software offset until `/robotiq_ft_streamer/zero` is called explicitly. It
publishes `/robotiq_ft_sensor/wrench` in `ft_measurement_frame`; this is
distinct from the official UR driver's
`/force_torque_sensor_broadcaster/wrench` topic.

For UR-only diagnostics without the external sensor, disable it explicitly:

```bash
ros2 launch ur5_workcell_bringup hardware.launch.py \
  robot_ip:=<robot-ip> \
  launch_ft_sensor:=false
```

The FT node can also be launched by itself while an existing UR bringup remains
running:

```bash
ros2 launch robotiq_ft_streamer ft_streamer.launch.py \
  robot_ip:=<robot-ip>
```

## Robotiq 3F gripper

The authoritative description uses the physically fitted articulated current
`AGS_*` model. Its zero state reproduces the previous fixed Basic/open pose.
The mapper uses actual A/B/C/S status once the connected gripper is activated;
before that, it publishes the reference pose (`A=B=C=6`, `S=137`) and sends no
command.

Normal bringup connects the gripper without activating or moving it:

```bash
ros2 launch ur5_workcell_bringup hardware.launch.py \
  robot_ip:=<robot-ip> \
  launch_gripper:=true \
  gripper_ip:=<verified-gripper-ip>
```

Verify `/robotiq_3f/status`, the 10 Hz update rate, fault state, and reconnect
behavior before commanding it. Launch sends no gripper command. Activation is
an explicit operation and can cause physical finger motion:

```bash
ros2 service call /robotiq_3f/activate std_srvs/srv/Trigger '{}'
```

Do not call activation until the gripper is clear of
the robot, table, people, and loose objects and the status-only gate has passed.

The standard Pinch-mode compatibility action accepts an opening coordinate in metres
and per-finger maximum effort in newtons:

```bash
ros2 action send_goal /robotiq_3f/gripper_command \
  control_msgs/action/GripperCommand \
  "{command: {position: 0.0775, max_effort: 30.0}}" \
  --feedback
```

Defaults are `0.0..0.155 m`, `15..60 N`, `30 N` when `max_effort` is zero,
and native speed 20. Every standard goal selects Pinch mode. The effective gap
mapping is `raw 0 = 0.155 m` open and `raw 112 = 0.0 m` closed because the
recorded real Pinch pose saturates there despite the nominal 0..255 command
scale. Use
`/robotiq_3f/move` for explicit mode selection or any advanced feature.

## Robot calibration

The current robot generated `ur5_calibration.generated.yaml` with hash
`calib_16683543926985068857`. Its values are numerically equivalent to the
canonical `ur5_calibration.yaml`, so bringup can continue using its canonical
default. The generated file is retained as provenance.

Generate calibration to a new source file first so the copied legacy file is
not overwritten accidentally when calibrating another robot in the future:

```bash
ros2 launch ur_calibration calibration_correction.launch.py \
  robot_ip:=<robot-ip> \
  target_filename:=/workspaces/ur5_ros2/ur5_ws/src/ur5_workcell/descriptions/ur5_workcell_description/config/ur5_calibration.generated.yaml
```

The generated file can be exercised without replacing the canonical default:

```bash
ros2 launch ur5_workcell_bringup hardware.launch.py \
  robot_ip:=<robot-ip> \
  kinematics_params_file:=/workspaces/ur5_ros2/ur5_ws/src/ur5_workcell/descriptions/ur5_workcell_description/config/ur5_calibration.generated.yaml
```

Inspect and record the generated hash before promoting the file to
`ur5_workcell_description/config/ur5_calibration.yaml` and rebuilding the
description package.
