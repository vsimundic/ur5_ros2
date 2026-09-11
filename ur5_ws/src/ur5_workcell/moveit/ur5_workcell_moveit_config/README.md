# UR5 workcell MoveIt configuration

This package plans the six UR joints from `base_link` to `tool0` using the
authoritative `ur5_workcell_description`. The Robotiq 3F links participate in
collision checking but are not a MoveIt planning group; its existing action
interfaces remain responsible for gripper commands.

The OMPL pipeline uses `RRTstarkConfigDefault` as the default planner for
`ur_manipulator`. `RRTConnectkConfigDefault` remains available for faster
interactive planning through the RViz planning-library selector or a planning
request's planner ID.

The authoritative description includes the fixed workcell table as collision
geometry. It spans 0.9 m across base X and 1.5 m along base Y, extends from
`z=-0.9` to the mounting plane at `z=0`, and is centered at `y=-0.54`. The
robot mounting frame is 0.21 m inboard from the short edge and rotated 180
degrees relative to the world-fixed table. Only the
intentional table-to-base-casting contact is disabled in the SRDF.

Start normal hardware bringup without its general RViz instance:

```bash
ros2 launch ur5_workcell_bringup hardware.launch.py \
  launch_rviz:=false
```

Then start MoveIt in another sourced terminal:

```bash
ros2 launch ur5_workcell_moveit_config moveit.launch.py
```

Alternatively, start MoveIt with workcell bringup in one command:

```bash
ros2 launch ur5_workcell_bringup hardware.launch.py \
  launch_rviz:=false launch_moveit:=true
```

The scaled trajectory controller is activated by normal bringup and MoveIt can
execute a planned trajectory. Keep the robot supervised and its workspace clear.
