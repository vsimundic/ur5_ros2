# Robots and Cubes

This directory is the root of the task-specific Robots and Cubes application.
It is an organizational directory, not a ROS 2 package. Colcon will discover
ROS packages added below it recursively.

Keep the application, its web frontend, editable configuration, and runtime
data under this directory. Continue to reuse the task-neutral robot, MoveIt,
simulation, and peripheral packages under `ur5_ws/src/ur5_workcell/`.

The approved ROS package prefix is `robots_and_cubes_*`. Current Phase 2
packages are:

- `robots_and_cubes_config`: strict YAML loading and immutable configuration;
- `robots_and_cubes_game`: board/cube models, exact coordinate transforms,
  seeded round generation, and the game state machine.

Editable files are in `config/`. The current implementation has no ROS nodes,
MoveIt integration, driver clients, gripper clients, or execution path.
