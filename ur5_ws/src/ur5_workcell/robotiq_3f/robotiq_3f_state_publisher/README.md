# robotiq_3f_state_publisher

This ROS 2 C++ node converts the Robotiq register feedback on
`/robotiq_3f/status` into the eleven movable joints of the current `AGS_*`
description. Finger A is the fixed-base opposing finger. Fingers B and C are
the outer pair and receive equal/opposite scissor angles.

The installed mapping is fitted from the physical samples recorded on
2026-09-04. It preserves the reviewed Basic/open assembly at the observed
`A=B=C=6` and `S=137`. Basic and Wide supplied the full finger-flexion curve;
reported mode 1 selects the separately fitted Pinch curve near its early travel
limit, and Scissor plus the Wide/Pinch mode anchors supplied the lateral curve.
The mapper interpolates between samples and holds the sampled endpoint outside
the fitted range. Request saturation is handled naturally because mapping
always uses the actual A/B/C/S feedback.

The mapping is a manually fitted collision/visualization approximation, not a
measurement of the gripper's closed internal linkage. Contacted-object poses,
individual control, and repeatability still require comparison before the
joint states are used for tight-clearance collision decisions.

The node uses actual feedback rather than requested positions and ignores
unconnected or non-activated status by default. Before the first valid status,
it publishes the reviewed reference pose so the articulated description has a
complete TF tree even when the gripper backend is disabled. It never commands
the gripper.

```bash
ros2 launch robotiq_3f_state_publisher joint_states.launch.py
```

Edit `config/joint_mapping.yaml` to refine the mapping without recompiling.
