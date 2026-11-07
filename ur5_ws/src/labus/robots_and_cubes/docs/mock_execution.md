# Hardware-free mock execution

`robots_and_cubes_mock_execution` is an application simulation of the existing
`ExecutePickPlace` action. It is not UR `use_mock_hardware`, Gazebo, fake
ros2_control, MoveIt plan-only mode, or a physical-robot test. It starts no UR
driver, MoveIt component, controller client, Modbus client, gripper client,
dashboard/safety service, FT/camera process, or hardware IP connection.

Only `MOCK` is implemented. Passing `execution_mode:=PLAN_ONLY` or `REAL` to
the mock launch fails closed; it never silently selects a stronger mode. The
editable `application.execution_mode` must also explicitly be `MOCK`; supported
future values are `PLAN_ONLY` and `REAL`, neither of which has an executor in
this phase. Synthetic mock readiness is strictly application-only and can never
satisfy real-hardware readiness. The action remains the same
`ExecutePickPlace` contract that future real execution must implement.

## Start a mock backend

Inside the normal development container, after building and sourcing:

```bash
cd /workspaces/ur5_ros2/ur5_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=45
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 launch robots_and_cubes_bringup mock_game.launch.py \
  user_settings_path:=/workspaces/ur5_ros2/ur5_ws/src/labus/robots_and_cubes/config/user_settings.yaml \
  child_text_path:=/workspaces/ur5_ros2/ur5_ws/src/labus/robots_and_cubes/config/child_text_hr.yaml \
  event_log_path:=/tmp/robots_and_cubes_mock_events.jsonl
```

This launch contains only the game manager, synthetic action server, and the
browser application gateway. It starts no robot or hardware client. The
normal editable `mock.movement_duration_seconds` is the total synthetic
operation duration, divided over the eight action stages. Use a small positive
value in a copied settings file for automated demonstrations.

The normal service flow is `generate_round`, `confirm_physical_setup`,
`submit_child_selection`, and `get_game_state`. `confirm_physical_setup`
performs mock-only consistency preflight and unlocks the child flow. The latest
complete `game_state` snapshot remains transient-local and can also be fetched
with `get_game_state`; `motion_stage` exposes application states such as
planning, grasping, and delivering without controller detail. JSONL events use
the ordinary game event model at the supplied path.

In a second terminal in that same isolated domain, execute the full Standard
success path through the real ROS manager/action-server boundary:

```bash
cd /workspaces/ur5_ros2/ur5_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=45
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 run robots_and_cubes_mock_execution mock_backend_smoke_test
```

## Deterministic outcome injection and recovery

Before submitting a selection, configure exactly the next action outcome:

```bash
ros2 service call /configure_mock_outcome \
  robots_and_cubes_interfaces/srv/ConfigureMockOutcome \
  "{request_id: mock-fail-1, outcome: 1, failure_stage: GRASPING, use_explicit_physical_progress: false, physical_progress: 0}"
```

`outcome` is `0` success, `1` failure, or `2` cancellation. Supported stages
are the action's `PLANNING`, `MOVING_TO_PREGRASP`, `DESCENDING`, `GRASPING`,
`LIFTING`, `MOVING_TO_DESTINATION`, `RELEASING`, and `RETREATING`. The
configuration is consumed once. An action client may also cancel a live goal;
the server checks cancellation between short bounded stage waits and never
continues to success afterward.

Failure before grasp is retryable and does not consume an attempt. Ambiguous
physical progress enters reconciliation. `RETRY_SAFE` means the operator
confirmed the source condition. `CUBE_HELD_OR_TRANSPORTED` and
`CUBE_AT_DESTINATION` record the observation and close the round rather than
blindly reissuing the pick. `ABORT_REQUIRED` also closes the round. No physical
recovery motion is available in this phase.
