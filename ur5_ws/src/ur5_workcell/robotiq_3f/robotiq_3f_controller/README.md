# robotiq_3f_controller

Backend-neutral C++ controller for the Robotiq 3F. It relays complete status on
`/robotiq_3f/status` and provides:

- `/robotiq_3f/activate` (`std_srvs/srv/Trigger`)
- `/robotiq_3f/deactivate` (`std_srvs/srv/Trigger`)
- `/robotiq_3f/stop` (`std_srvs/srv/Trigger`)
- `/robotiq_3f/move` (`robotiq_3f_interfaces/action/Move`)
- `/robotiq_3f/gripper_command` (`control_msgs/action/GripperCommand`)

The launch connects the driver and controller without sending a command:

```bash
ros2 launch robotiq_3f_controller hardware.launch.py \
  gripper_ip:=<verified_gripper_ip>
```

Calling `activate` explicitly performs the required reset-then-activation
sequence. Physical finger motion can occur during activation. A cancelled or
timed-out move sends a `go_to=false` stop command
when the same backend connection is still available.

Reset and activation each receive the configured `activation_timeout_s` time
budget. The default is 30 seconds because physical auto-calibration can take
longer than the original combined 15-second budget.

Python programs use the generated `robotiq_3f_interfaces` action and message
classes with `rclpy`; no C++ bindings are required.

## Standard GripperCommand compatibility

`/robotiq_3f/gripper_command` is a deliberately reduced Pinch-mode adapter for
MoveIt and generic ROS 2 clients. The native `/robotiq_3f/move` action remains
the interface for explicit mode selection, Basic, Wide, Scissor, individual control, and native speed or
force values.

Every accepted standard goal selects native Pinch mode. The standard action
retains the same activation requirement,
single-operation arbitration, timeout, cancellation-stop, reconnect, and fault
behavior as the native action. Its SI conversion defaults are based on the
legacy 3F references and are configurable:

- position: the `0.0 m` closed to `0.155 m` open gap is linearly mapped to the
  measured effective Pinch travel, raw 112..0;
- maximum effort: `15..60 N` per finger, linearly mapped to raw 0..255;
- `max_effort=0` selects the configured `30 N` default; and
- speed uses the configured conservative raw value `20` because the standard
  action has no speed field.

Goals outside the configured position/effort range or containing non-finite
values are rejected rather than clamped. Status provides only a raw motor
current byte, not force in newtons, so result/feedback `effort` is honestly
reported as zero. `stalled` means the native status reported object contact;
`reached_goal` means it reported the requested position reached.

Although the nominal command scale defines raw 255 as closed, the recorded real
Pinch motion reaches its closed pose around actual A=112 and B/C=113. The
compatibility action therefore uses configurable `gripper_command_closed_raw`
with default 112. Feedback above that value is reported as zero gap.

After supervised activation, an explicit half-open 30 N request is:

```bash
ros2 action send_goal /robotiq_3f/gripper_command \
  control_msgs/action/GripperCommand \
  "{command: {position: 0.0775, max_effort: 30.0}}" \
  --feedback
```

The standalone launch also starts `robotiq_3f_state_publisher` by default. It
only reads status and publishes the fitted articulated pose. Disable it
with `launch_joint_state_publisher:=false` when another workcell launch owns
that publisher.
