# Robots and Cubes

This directory contains the task-specific Robots and Cubes application. It is
an organizational directory, not a ROS 2 package; colcon discovers the packages
below it recursively. Shared robot, MoveIt, simulation and peripheral packages
remain under `ur5_ws/src/ur5_workcell/`.

## Current implementation

- `robots_and_cubes_config`: validated YAML configuration and runtime schemas.
- `robots_and_cubes_game`: game models, round generation, state machine and ROS manager.
- `robots_and_cubes_interfaces`: application messages, services and pick/place action.
- `robots_and_cubes_calibration`: grid calibration, teaching and persistence logic,
  with an injectable adapter; no runnable calibration ROS node yet.
- `robots_and_cubes_mock_execution`: synthetic pick/place action server and mock readiness.
- `robots_and_cubes_ui_gateway`: HTTP/WebSocket gateway to application ROS interfaces.
- `robots_and_cubes_bringup`: mock backend and gateway launch.
- `web/robots_and_cubes_web`: React child and operator interfaces.

Only `MOCK` execution is implemented. The mock launch starts no robot drivers,
MoveIt or hardware clients. `PLAN_ONLY` and `REAL` execution are unavailable.
Commissioning values in `config/robot_commissioning.yaml` include provisional
geometry and unset motion/gripper parameters; they are not validated hardware defaults.

## Build and run

In the project development container, build and source the ROS workspace:

```bash
cd /workspaces/ur5_ros2/ur5_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-up-to robots_and_cubes_bringup
source install/setup.bash
```

Install frontend dependencies from the committed lockfile and build the UI:

```bash
cd /workspaces/ur5_ros2/ur5_ws/src/labus/robots_and_cubes/web/robots_and_cubes_web
npm ci
npm run build
```

`node_modules/`, `dist/` and TypeScript build metadata are generated locally
and ignored by Git. Commit `package.json` and `package-lock.json` together when
changing dependencies. Rebuild `dist/` after changing frontend source.

See [mock execution](docs/mock_execution.md) for launch and smoke-test commands,
and [UI gateway](docs/ui_gateway.md) for serving the built UI, development mode
and operator authorization. [Calibration](docs/calibration.md),
[coordinate systems](docs/coordinate_systems.md) and the
[operator guide](docs/operator_guide.md) describe calibration/teaching logic and
its remaining integration requirements.

Editable application configuration lives in `config/`. Generated calibration,
teaching and event data belong in `runtime_data/` and must remain untracked.

## Frontend checks

Run `npm run typecheck`, `npm run lint`, `npm test` and `npm run build` from the
frontend directory. ROS integration checks require the sourced ROS environment.
