# Robotiq 3F description

This package provides the current-revision `AGS_*` Robotiq 3-Finger Adaptive
Gripper geometry ported from the legacy ROS 1 workcell. The default macro is
articulated, while `articulated:=false` restores the original fixed collision
baseline. It intentionally does not provide a driver, transmissions, or
`ros2_control` interfaces.

The articulated zero state is algebraically identical to the reviewed fixed
assembly and represents Basic/open: finger feedback was approximately
`A=B=C=6`, with scissor-axis feedback `S=137`. Physical fitting on 2026-09-04
moved every proximal-to-middle rotation center by +11.62 mm on its local X
axis. A compensating fixed mesh offset preserves the original assembled pose
at zero. The remaining pivots, axes, limits, and closed-linkage approximation
still require CAD or physical dimensional validation before being treated as
fully calibrated.

Runtime joint states are produced by `robotiq_3f_state_publisher`. It expands
the four measured actuator coordinates A/B/C/S into eleven physical joints.

The two cable-plug cylinders are part of this description because they are
physical collision geometry attached to the gripper palm. Their dimensions,
poses, masses, and inertias are migrated values and require physical or CAD
verification before dynamics-sensitive simulation.

The mesh files were copied from the legacy `robotiq_3f_description` package,
which declares the BSD license. Only the metre-scaled visual and collision
meshes used by the legacy xacro were transferred.
