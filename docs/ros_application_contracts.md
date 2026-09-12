# Robots and Cubes ROS application contracts

`robots_and_cubes_interfaces` defines the application boundary. It does not
contain UR, MoveIt, controller, Modbus, or gripper-register details.

## ExecutePickPlace

`ExecutePickPlace` is the only long-running physical-operation contract. Its
goal identifies a request, round, cube, grid cell, destination policy, and
configuration/calibration revisions. It deliberately contains no game
correctness field. The manager decides whether a completed cube operation was
correct.

Feedback stages are `PLANNING`, `MOVING_TO_PREGRASP`, `DESCENDING`,
`GRASPING`, `LIFTING`, `MOVING_TO_DESTINATION`, `RELEASING`, and `RETREATING`.
The result uses `SUCCEEDED`, `CANCELED`, or `FAILED`, a stable error code, and
`physical_progress`. `MAY_HAVE_GRASPED`, `MAY_HAVE_TRANSPORTED`, and
`MAY_HAVE_RELEASED` require operator reconciliation before retry.

## Game manager and snapshots

`robots_and_cubes_game.game_manager.GameManager` owns external-intent
serialization around the pure state machine. It generates rounds, validates
round/request identities, locks input before dispatch, and commits a wrong
attempt only when the action reports successful physical completion.

`GameStateSnapshot` is a complete, versioned state: round identity, mode,
origin/orientation, cubes and visual kinds, game coordinates, answer state,
attempts, operation identity/state, readiness, and a recoverable error summary.
`RosGameManagerNode` publishes it on `game_state` with reliable transient-local
QoS and provides `get_game_state` for explicit reconnect/fetch behavior.

## Intents and recovery

The narrow service set is `generate_round`, `confirm_physical_setup`,
`submit_child_selection`, `retry_operation`, `reconcile_operation`,
`abort_round`, and `get_game_state`. Every state-changing request carries a
request ID; repeated IDs return the current snapshot without dispatching a
second operation. Requests for a different round are rejected as stale.

Planning failures, cancellation, gripper failures, and execution failures enter
recoverable `ROBOT_ERROR` without consuming an attempt. The round, selected
cube, attempt count, request ID, and operation ID remain available for the
operator. Phase 3 only records whether a retry is safe; it does not perform
physical reconciliation or motion.
