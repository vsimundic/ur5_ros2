# UR5 workcell description

This package assembles the installed ROS 2 Universal Robots UR5 description
with the migrated workcell tooling, sensors, cable-plug collision geometry,
and the current robot calibration. A freshly generated calibration matched the
canonical file's `calib_16683543926985068857` hash and numerical parameters.

`urdf/workcell.urdf.xacro` is the standalone authoritative description.
`urdf/ur5_workcell_macro.xacro` is reusable and accepts an arbitrary parent
frame. The standalone wrapper creates `world` only because the installed UR
macro requires a parent link.

`urdf/workcell_control.urdf.xacro` is the real/mock hardware wrapper. It reuses
the same physical macro and adds the official Universal Robots `ros2_control`
system. The view-only wrapper remains free of control elements.

This package contains no Gazebo plugin, hardware driver implementation, table,
wall, or task object. Simulation and real-hardware wrappers must reuse this
physical chain rather than fork it.

The FT/coupler/gripper transforms remain migrated values that require final
physical or CAD verification. The camera mount is derived from the calibrated
2026-07-24 `tool0 -> camera_color_optical_frame` pose for L515 serial
`f1062071`. The source `.npy` contains a uniform scale in its rotation block;
`config/camera_extrinsics.yaml` records the source checksum, scale removal,
normalized rigid transform, device optical offset, and resulting
`tool0 -> camera_link` xacro pose. The `grasp_tcp` default is the location of
the legacy tool marker and remains explicitly provisional.
