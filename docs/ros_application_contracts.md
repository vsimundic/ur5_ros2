# Robots and Cubes ROS application contracts

`robots_and_cubes_interfaces` defines the application boundary. It does not
contain UR, MoveIt, controller, Modbus, or gripper-register details.

## ExecutePickPlace

`ExecutePickPlace` is the only long-running physical-operation contract. Its
goal identifies a request, operation, round, cube, grid cell, destination policy, and
configuration/calibration revisions. It deliberately contains no game
correctness field. The manager decides whether a completed cube operation was
correct.

Feedback stages are `PLANNING`, `MOVING_TO_PREGRASP`, `DESCENDING`,
`GRASPING`, `LIFTING`, `MOVING_TO_DESTINATION`, `RELEASING`, and `RETREATING`.
The result uses `SUCCEEDED`, `CANCELED`, or `FAILED`, a stable error code, and
`physical_progress`. `MAY_HAVE_GRASPED`, `MAY_HAVE_TRANSPORTED`, and
`MAY_HAVE_RELEASED` require operator reconciliation before retry.

Phase 5's application mock implements this same action; it does not define a
second mock action. It permits one active operation, publishes every defined
feedback stage, and exposes one-shot deterministic development outcomes through
`configure_mock_outcome`. The outcome service maps directly to existing result
and physical-progress fields. It never receives game correctness, score, or
attempt information.

## Game manager and snapshots

`robots_and_cubes_game.game_manager.GameManager` owns external-intent
serialization around the pure state machine. It generates rounds, validates
round/request identities, locks input before dispatch, and commits a wrong
attempt only when the action reports successful physical completion.

`GameStateSnapshot` is a complete, versioned state: round identity, mode,
origin/orientation, cubes and visual kinds, game coordinates, answer state,
attempts, operation identity/state, readiness, and a recoverable error summary.
Mode numeric values remain stable for Easy (0), Beginner (1), Standard (2),
and Challenge (3); Spatial is appended as value 4. Standard and Challenge
retain coordinate-pair answers, while Spatial carries both its target shape and
relative target coordinate for the Croatian child prompt.
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
operator. Phase 3 defined the structured retry/reconciliation contract; Phase 5
exercises it through synthetic execution. The mock records reconciliation
outcomes but has no physical recovery motion. A future ambiguous real physical
state still requires explicit operator reconciliation and must never be treated
as recovered by mock behavior.
