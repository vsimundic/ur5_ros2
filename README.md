# UR5 ROS 2 workcell

ROS 2 Jazzy workspace for the physical UR5 workcell with a Robotiq 3F
gripper, Robotiq FT300s TCP stream, RealSense L515 description, and XELA
tactile-sensor description.

The reusable hardware stack is task-neutral. Authoritative MoveIt planning and
the first Gazebo arm-simulation phase are implemented; task packages and
simulated gripper/sensor behavior are not complete yet.

## Safety and command ownership

Real hardware can move whenever an activation service, action, trajectory, or
dashboard command is sent. Keep the tool clear, supervise every initial test,
keep the emergency stop accessible, and use conservative robot speed scaling.

The launch sends no motion command by default:

- the UR arm trajectory controller is active but receives no trajectory;
- the 3F driver connects and monitors but does not activate or move the
  gripper; and
- FT startup zeroing is disabled.

Use exactly one gripper command source. Stop PolyScope programs containing
Robotiq commands, the Robotiq UI, legacy ROS 1 drivers, and other gripper
clients before commanding `/robotiq_3f/*` from ROS 2. Competing PolyScope and
ROS commands were observed to cause jitter, overwritten requests, and failed
activation handshakes.

## Container and workspace

Build and start the development container from the repository root:

```bash
./docker/build_docker.sh
./docker/run_docker.sh
```

The launcher uses host networking, NVIDIA GPU access, privileged mode, the
mounted workspace, and the configured ROS domain/RMW. It also mounts the legacy
project read-only. These defaults can be overridden with environment variables
documented in `docker/run_docker.sh`.

Inside the container, build and source the workspace:

```bash
cd /workspaces/ur5_ros2/ur5_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

Source both setup files in every new terminal. After rebuilding a C++ package,
restart its running node; a running process does not load a newly built binary.

## Description-only check

This starts no hardware or simulation nodes:

```bash
ros2 launch ur5_workcell_description view_description.launch.py
```

An offline bringup/controller check can use mock UR hardware:

```bash
ros2 launch ur5_workcell_bringup hardware.launch.py \
  robot_ip:=127.0.0.1 \
  use_mock_hardware:=true \
  launch_ft_sensor:=false \
  launch_gripper:=false \
  launch_rviz:=true
```

## Gazebo simulation

Stop real-hardware bringup before starting simulation so real and simulated
controllers cannot occupy the same ROS graph. Then launch the authoritative
workcell, Gazebo, the simulated arm controller, MoveIt, and RViz:

```bash
ros2 launch ur5_workcell_sim sim.launch.py
```

In RViz, use the `ur_manipulator` planning group and plan to `tool0`. Confirm
the simulation interfaces from another sourced terminal:

```bash
ros2 service call /controller_manager/list_controllers \
  controller_manager_msgs/srv/ListControllers '{}'
ros2 topic hz /joint_states
ros2 topic hz /clock
```

The joint-state broadcaster and scaled trajectory controller should both be
active. A headless launch is also available:

```bash
ros2 launch ur5_workcell_sim sim.launch.py \
  gazebo_gui:=false launch_rviz:=false
```

The current simulation controls only the six UR joints and uses the fixed 3F
pose. The mounted camera publishes simulated 640 x 480 color and registered
depth at 30 Hz; the FT and tactile components remain geometry rather than
simulated sensors. See
`ur5_ws/src/ur5_workcell/simulation/ur5_workcell_sim/README.md` for details.

## Normal hardware bringup

The installed configuration currently contains the verified robot and gripper
addresses. Normal bringup starts the UR driver, robot description, active arm
trajectory controller, FT streamer, 3F driver/controller/state mapper, and
optionally RViz. It does not send an arm trajectory or activate the gripper:

```bash
ros2 launch ur5_workcell_bringup hardware.launch.py launch_rviz:=true
```

Equivalent explicit endpoint overrides are:

```bash
ros2 launch ur5_workcell_bringup hardware.launch.py \
  robot_ip:=192.168.88.245 \
  gripper_ip:=192.168.88.237 \
  launch_ft_sensor:=true \
  launch_gripper:=true \
  launch_rviz:=true
```

The canonical UR calibration hash is
`calib_16683543926985068857`. Stop if the driver reports a mismatch.

The camera is enabled in the current cell defaults; suppress it with
`launch_camera:=false` for UR-only diagnostics.

## RealSense L515 bringup and checks

The image pins librealsense 2.54.2 and the RealSense ROS wrapper 4.54.1 because
newer librealsense releases no longer contain L515 support. Both are built from
source during `./docker/build_docker.sh`; the SDK uses its RSUSB user-space USB
backend and does not require a patched host kernel driver. Rebuild and recreate
containers made before this change.

Plug the L515 into a USB 3 port before starting the container. The Docker
launcher bind-mounts `/dev/bus/usb` so the privileged container can also see
devices reconnected after startup. Confirm discovery without starting ROS:

```bash
lsusb | grep '8086:0b64'
pkg-config --modversion realsense2
ros2 pkg prefix realsense2_camera
rs-enumerate-devices -s
```

The version and prefix commands must report `2.54.2` and
`/opt/realsense_ws/install/realsense2_camera`. If `lsusb` sees `8086:0b64` but
`rs-enumerate-devices` does not enumerate it, reconnect the camera directly to
a USB 3 port and inspect its firmware and USB descriptor output with
`rs-enumerate-devices` before starting ROS. Do not update L515 firmware through
a newer SDK.

Start the normal passive workcell bringup with the optional camera enabled:

```bash
ros2 launch ur5_workcell_bringup hardware.launch.py \
  launch_camera:=true \
  launch_rviz:=true
```

The verified L515 defaults preserve the legacy topic interface while using
profiles supported by the installed device: 640 x 480 color and depth at
30 Hz, with depth alignment enabled. The device rejects the legacy 640 x 480
depth-at-15-Hz request. Point-cloud publication is currently disabled; pass
`camera_pointcloud:=true` when it is needed. The RealSense node is
`/camera/camera`, while its streams remain under `/camera/*`. Check the node,
topics, message rates, image metadata, and, when enabled, point cloud:

```bash
ros2 node info /camera/camera
ros2 topic list | grep '^/camera/'
ros2 topic hz /camera/color/image_raw
ros2 topic hz /camera/depth/image_rect_raw
ros2 topic hz /camera/aligned_depth_to_color/image_raw
ros2 topic echo /camera/color/camera_info --once
ros2 topic echo /camera/depth/color/points --once --field header
```

For an isolated camera-only test, do not try to pass an empty namespace on the
command line; ROS 2 rejects an empty `name:=value` launch argument. Use:

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

Do not run this standalone launch concurrently with workcell bringup using
`launch_camera:=true`.

The authoritative robot description owns `tool0 -> camera_link`; the camera
node owns transforms below `camera_link`. Verify both ends of that one connected
tree and check that there is only one publisher for `/tf_static` transforms:

```bash
ros2 run tf2_ros tf2_echo tool0 camera_link
ros2 run tf2_ros tf2_echo camera_link camera_color_optical_frame
ros2 topic info /tf_static --verbose
```

In RViz, add Image displays for the two image topics and a PointCloud2 display
for `/camera/depth/color/points`. Confirm that color is upright, aligned depth
tracks the same scene, the cloud follows the wrist-mounted camera when the arm
is moved under separate supervised control, and no second node publishes a
competing `tool0 -> camera_link` transform. The mount now uses the 2026-07-24
extrinsic calibration for L515 serial `f1062071`: the supplied matrix is the
`camera_color_optical_frame` pose expressed in `tool0`. Its legacy rotation
scale is removed before conversion to a rigid transform, and the full
provenance and derived `camera_link` pose are recorded in
`ur5_workcell_description/config/camera_extrinsics.yaml`. Visually verify the
calibrated overlay before metric perception or manipulation.

## Health checks

Confirm the expected nodes and endpoints:

```bash
ros2 node list
ros2 action list -t
ros2 service list -t
```

Check UR state without commanding motion:

```bash
ros2 topic echo /io_and_status_controller/robot_mode --once
ros2 topic echo /io_and_status_controller/safety_mode --once
ros2 topic echo /io_and_status_controller/robot_program_running --once
ros2 topic echo /speed_scaling_state_broadcaster/speed_scaling --once
ros2 topic echo /joint_states --once
```

List controllers even when the optional `ros2 control` CLI extension is not
installed:

```bash
ros2 service call /controller_manager/list_controllers \
  controller_manager_msgs/srv/ListControllers '{}'
```

Before arm motion, verify that exactly the intended trajectory controller is
active. The normal safe launch leaves `scaled_joint_trajectory_controller`
inactive.

Check the external FT stream:

```bash
ros2 topic echo /robotiq_ft_sensor/wrench --once
ros2 topic hz /robotiq_ft_sensor/wrench
```

The workcell FT topic is `/robotiq_ft_sensor/wrench` in
`ft_measurement_frame`. Do not confuse it with the official UR driver's
`/force_torque_sensor_broadcaster/wrench` topic.

Check the 3F connection and approximately 10 Hz status stream:

```bash
ros2 topic echo /robotiq_3f/status --once
ros2 topic hz /robotiq_3f/status
```

A commandable gripper must report `connected: true`, `activated: true`,
`initialization_status: 3`, and `fault_status: 0`.

## FT zeroing

Unload the tool and keep it stationary, then request the validated 100-sample
software zero:

```bash
ros2 service call /robotiq_ft_streamer/zero std_srvs/srv/Trigger '{}'
```

The streamer suppresses wrench publication while collecting the bias.

## Robotiq 3F control

Activation performs reset followed by initialization and can move the fingers:

```bash
ros2 service call /robotiq_3f/activate std_srvs/srv/Trigger '{}'
```

Stop and deactivate are explicit operations:

```bash
ros2 service call /robotiq_3f/stop std_srvs/srv/Trigger '{}'
ros2 service call /robotiq_3f/deactivate std_srvs/srv/Trigger '{}'
```

The standard action always selects Pinch mode. Its verified physical-gap
mapping is `0.155 m = raw 0` open, `0.0775 m = raw 56` half-open, and
`0.0 m = raw 112` closed. Effort is per finger; use 30 N for normal supervised
tests:

```bash
# Open
ros2 action send_goal /robotiq_3f/gripper_command \
  control_msgs/action/GripperCommand \
  '{command: {position: 0.155, max_effort: 30.0}}' --feedback

# Half-open
ros2 action send_goal /robotiq_3f/gripper_command \
  control_msgs/action/GripperCommand \
  '{command: {position: 0.0775, max_effort: 30.0}}' --feedback

# Close
ros2 action send_goal /robotiq_3f/gripper_command \
  control_msgs/action/GripperCommand \
  '{command: {position: 0.0, max_effort: 30.0}}' --feedback
```

The gripper exposes raw motor current, not measured force in newtons, so action
feedback/result effort is reported as zero. A contacted object is reported as
`stalled: true`, `reached_goal: false`, with a successful action result.

### Cancel an active standard goal

In this environment, interrupting `ros2 action send_goal` with SIGINT can hang
inside the CLI cancellation handler. Cancel reliably from another terminal via
the action's hidden cancel service:

```bash
ros2 service call \
  /robotiq_3f/gripper_command/_action/cancel_goal \
  action_msgs/srv/CancelGoal \
  '{goal_info: {goal_id: {uuid: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}, stamp: {sec: 0, nanosec: 0}}}'
```

The zero UUID and timestamp cancel every active goal on this one action
endpoint. A successful cancellation stops physical motion, returns action
status `CANCELED`, sets `go_to: false`, and leaves the actual position short of
the requested target. Keep `/robotiq_3f/stop` ready as the independent fallback.

Calling `/robotiq_3f/stop` alone stops the hardware but does not cancel the
action goal; that goal will remain active until it times out and returns
`ABORTED`.

### Native 3F action

Use `/robotiq_3f/move` for Basic, Pinch, Wide, Scissor, individual finger
control, individual scissor control, and native raw speed/force fields. Modes
are Basic `0`, Pinch `1`, Wide `2`, and Scissor `3`.

Example validated asymmetric Basic pose:

```bash
ros2 action send_goal /robotiq_3f/move \
  robotiq_3f_interfaces/action/Move \
  '{
    mode: 0,
    individual_finger_control: true,
    individual_scissor_control: true,
    position_a: 30, speed_a: 20, force_a: 85,
    position_b: 60, speed_b: 20, force_b: 85,
    position_c: 90, speed_c: 20, force_c: 85,
    position_scissor: 160, speed_scissor: 20, force_scissor: 85,
    timeout: {sec: 20, nanosec: 0}
  }' --feedback
```

This exact command was physically validated: actual A/B/C/S reached
`30/60/90/160`, the articulated RViz model followed the distinct bends and
opposed scissor motion, and no fault occurred.

## UR arm control

Arm motion remains opt-in because a trajectory must be requested explicitly.
For a supervised MoveIt session, launch bringup with MoveIt enabled:

```bash
ros2 launch ur5_workcell_bringup hardware.launch.py \
  launch_moveit:=true \
  launch_rviz:=true
```

Prepare and run the pendant External Control program as required by the
official UR driver. Before every motion, verify robot/safety mode, program
state, calibration, current joints, speed slider, clear workspace, and the
active controller.

The execution endpoint is:

```text
/scaled_joint_trajectory_controller/follow_joint_trajectory
control_msgs/action/FollowJointTrajectory
```

Send only measured, collision-reviewed joint targets. A command template is
shown below deliberately with placeholders; do not paste it without replacing
all six values with a nearby supervised target in radians:

```bash
ros2 action send_goal \
  /scaled_joint_trajectory_controller/follow_joint_trajectory \
  control_msgs/action/FollowJointTrajectory \
  '{trajectory: {
    joint_names: [shoulder_pan_joint, shoulder_lift_joint, elbow_joint,
                  wrist_1_joint, wrist_2_joint, wrist_3_joint],
    points: [{
      positions: [J0, J1, J2, J3, J4, J5],
      time_from_start: {sec: 10, nanosec: 0}
    }]
  }}'
```

The authoritative MoveIt group plans the six UR joints from `base_link` to
`tool0`, by design. Direct real-hardware trajectories remain supervised
commissioning tools, not task-level motion.

## Current validation and next milestone

Real-hardware gates 1 through 7 are complete. The UR5, FT stream/zeroing/axes,
3F activation/motion, standard gap conversion, action cancellation,
contact-result semantics, individual finger control, individual scissor
control, and live articulated mapping have been supervised on the installed
cell. Power-cycle repeatability and photographic/dimensional gripper recording
were deliberately deferred.

The RealSense L515 image pipeline and calibrated TF overlay are validated.
Authoritative MoveIt planning and supervised execution to `tool0` are also
validated. The first Gazebo phase now spawns the complete workcell geometry and
executes six-joint MoveIt trajectories. The next simulation milestone is a 3F
backend with the same command/status contract as the real driver, followed by
simulated FT, camera, and tactile outputs where task testing requires them.

See `AGENTS.md` for architecture, migration history, open decisions, and the
full safety-gated roadmap.
