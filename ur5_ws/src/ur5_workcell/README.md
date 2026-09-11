# UR5 workcell packages

This directory groups task-neutral ROS 2 packages for the physical UR5
workcell. The extra directory levels do not change package names; colcon
discovers packages recursively. A subsystem with multiple packages keeps its
description, interfaces, driver, and future simulation backend together.

```text
ur5_workcell/
  descriptions/ur5_workcell_description/  # authoritative assembly
  bringup/ur5_workcell_bringup/            # top-level orchestration
  robotiq_3f/                              # description/API/driver/state mapping/calibration
  robotiq_ft/                              # description/TCP streamer
  realsense_l515/                          # description; bringup is future work
  xela_usp44/                              # description; driver is future work
```

Expected future groupings include `moveit/` and `simulation/`. Add a component
package to its subsystem grouping instead of recreating global `drivers/` or
`descriptions/` buckets. Task-specific packages should remain outside this
directory.

The older top-level `ur5_robotiq` and `ur5_robotiq_moveit_config` packages remain
in place until their mechanically divergent description, simulation, and
MoveIt configuration are deliberately migrated.
