# Robots and Cubes — Phase 1 Implementation Plan

Status: **Phase 2 implemented for the user-approved configuration and pure game-core scope.** This maps `docs/treasure_hunt_spec.md` onto the source and offline findings in [implementation_inventory.md](implementation_inventory.md). Existing UR, MoveIt, gripper, description and Docker infrastructure stays authoritative.

The application’s canonical product name is **Robots and Cubes**. New ROS packages and code namespaces use the `robots_and_cubes_*` prefix. All application source, frontend, editable configuration, and runtime-data directories live under `ur5_ws/src/labus/robots_and_cubes/`. The specification keeps its existing filename as the original requirements artifact.

## 1. Architecture and reuse

The new application should sit outside `ur5_ws/src/ur5_workcell/`, keeping reusable hardware packages task-neutral.

```text
React /kid and /operator
          |
    HTTP / WebSocket
          |
  robots_and_cubes_ui_gateway
          |
  robots_and_cubes_game -------- robots_and_cubes_calibration
          |                           |
  ExecutePickPlace action       measured state / TF
          |
  robots_and_cubes_motion
     |             |
 mock executor   MoveIt + gripper adapters
                       |
             existing workcell stack
```

| Existing package/component | Reuse decision |
|---|---|
| `ur5_workcell_description` and four component descriptions | Reuse robot/tool/table geometry, calibrated kinematics and frame tree. Add board/game objects through the application planning scene, not a competing robot description |
| `ur5_workcell_bringup` + installed official UR driver | Reuse explicit operator-started hardware orchestration. Do not add a replacement driver or automatic activation/recovery |
| `ur5_workcell_moveit_config` | Reuse `ur_manipulator`, KDL, `tool0`, collision geometry and scaled execution mapping; add an opt-in application planning profile later |
| `robotiq_3f_controller`, driver, interfaces, state publisher | Wrap public services/actions/status; keep register packing and mapping below the application |
| `ur5_workcell_sim` | Optional integration environment after hardware-free mock work; same gripper API, not proof of physical grasp success |
| `robotiq_ft_streamer`, RealSense | Preserve optional diagnostics/perception infrastructure. Neither is required to determine V1 manual board contents |
| `robotiq_3f_calibration` | Retain as a gripper geometry tool; do not repurpose it as grid calibration or game UI |
| Legacy packages | Leave intact; do not base the application on their divergent description, Servo, 2F driver or serial FT path |

## 2. Proposed package and file structure

All names below are **new proposed application components**, not claims about existing ROS endpoints. Create them incrementally in the specification's phases.

```text
ur5_ws/src/labus/robots_and_cubes/        # project grouping; not a ROS package
  robots_and_cubes_config/               # ament_python; Phase 2
    robots_and_cubes_config/
      models.py                         # typed config and runtime models
      loader.py                         # layered loading and validation
    config/
      user_settings.yaml
      robot_commissioning.yaml
      cell_commissioning.yaml
      child_text_hr.yaml
    test/
  robots_and_cubes_interfaces/           # ament_cmake / rosidl
    action/ExecutePickPlace.action
    msg/                                # state, selections, structured errors
    srv/                                # game/calibration/teaching operations
  robots_and_cubes_game/                 # ament_python
    robots_and_cubes_game/
      core/                             # no rclpy or driver dependencies
        coordinates.py
        models.py
        round_generator.py
        state_machine.py
      game_manager.py                   # ROS adapter around pure core
    test/
  robots_and_cubes_calibration/          # ament_python
    robots_and_cubes_calibration/
      geometry.py
      persistence.py
      calibration_manager.py
      teaching_manager.py
    test/
  robots_and_cubes_motion/               # ament_cmake, C++ MoveIt integration
    src/                                # action server, policy, scene, adapters
    scripts/mock_executor.py             # hardware-free action implementation
    include/robots_and_cubes_motion/
    test/
  robots_and_cubes_ui_gateway/           # ament_python, FastAPI + ROS adapter
    robots_and_cubes_ui_gateway/
    test/
  robots_and_cubes_bringup/              # ament_cmake launch/config installation
    launch/                             # explicit mock / plan-only / real modes
    config/                             # later application planning profile
  web/robots_and_cubes_web/              # React/TypeScript/Vite; not a ROS package
    src/                                # /kid and /operator
    tests/
  config/                               # externally editable deployment files
  runtime_data/
    calibration.yaml
    taught_poses.yaml
    events/                             # JSONL logs
docs/
  implementation_inventory.md
  implementation_plan.md
  configuration.md                      # Phase 2; further guides in later phases
```

The extra `robots_and_cubes_config` package is justified by Phase 2 and shared typed validation across game, calibration, motion and gateway. It prevents those packages depending on game logic just to load settings. Mock and gripper adapters do not need separate ROS packages. The web project is a separate build artifact; the ROS bringup package can later serve/install its built static output through the gateway. No new UR/gripper driver, robot description, database, automatic piece-placement system or perception package is necessary for V1.

## 3. Configuration ownership and persistence

Package `config/` files provide versioned defaults/templates. The operator-facing copy lives in `ur5_ws/src/labus/robots_and_cubes/config/`, already covered by Docker's project bind mount. Launch will accept explicit config/runtime paths; it must never overwrite an edited file with defaults. Defaults load first, then user configuration, commissioning configuration, cell configuration, calibration and taught poses. Invalid supplied values fail with property-specific diagnostics; they do not fall back silently.

| File | Owner and contents |
|---|---|
| `user_settings.yaml` | Normal game/board/cube settings, attempts/counts, generation rules, UI/mock timing, common clearances and validated default yaw |
| `robot_commissioning.yaml` | Mark `ADVANCED — change only during robot commissioning.` Discovered frame/group/planner/interface bindings, pen/tool transform, game joint ranges, excursion limits, approved speeds/tolerances and grasp policy |
| `cell_commissioning.yaml` | Advanced per-cell availability and optional yaw override, with provenance tied to geometry/calibration revision |
| `child_text_hr.yaml` | Central UTF-8 Croatian child copy; operator copy remains separate |
| `runtime_data/calibration.yaml` | Version, timestamp, P0/PX/PY, transform, quality, optional PXY and geometry/config identity |
| `runtime_data/taught_poses.yaml` | Actual captured home/safe joint states and destination poses, explicit frames and provenance |
| `runtime_data/events/*.jsonl` | Round seeds, selections, attempts, planners, motion results, errors and operator/calibration events |

Keep existing IPs, driver settings, factory calibration and gripper mapping in their current workcell packages. Application bindings reference the discovered interfaces; they do not become a second hardware configuration authority. Keep runtime data out of Git, write accepted data atomically, validate on reload and record schema/config revisions. No image rebuild is needed after settings edits, teaching or calibration. Application restart is adequate for MVP; do not hot-reload geometry during a round.

Resolve duplicate yaw examples in the specification with one rule: user default yaw applies unless an approved entry in the advanced cell file overrides it; the advanced policy validates the resulting orientation. Do not maintain two independent per-cell maps. Geometry or pen/TCP changes invalidate dependent calibration/commissioning. Unknown cells are unavailable for real play; an explicit synthetic all-cell map may exist only for mock fixtures.

Phase 2 should use strict typed models (Pydantic proposed; dependency must be declared). Validate cross-field feasibility, units, finite numbers, supported quarter turns, origin margins, attempts, exactly one green, dynamic answer count and forbidden low-level user overrides. Document a supported answer-count cap rather than claiming any touchscreen layout works. Physical dimensions may load from spec defaults, but these defaults are not physical commissioning evidence. Unknown safety values remain unset and block real readiness.

## 4. Pure game authority and ROS contracts

`robots_and_cubes_game/core/` owns deterministic integer grid↔game transforms, bounded seeded generation, immutable round identities, difficulty rules, attempts, removed cubes and state transitions. It imports no ROS, MoveIt or gripper modules. Use `A = R * H` with exact integer matrices; reflections exist only in educational coordinates, never in TF. Game origin rotation is independent of gripper yaw.

Preserve distinct mode rules: Easy red taps cause neither motion nor attempt loss; Beginner correctness uses target location, not color; Standard/Challenge answers come from actual generated cubes and are dynamic. Only a successfully completed wrong-cube operation consumes an attempt/removes an answer. Hardware errors enter `ROBOT_ERROR`, retaining the round and attempt. A partial physical operation must be reconciled before retry; do not blindly re-pick a cube already held or placed.

The ROS game manager serializes selections/operations, rejects stale round IDs and duplicate request IDs, and publishes a complete versioned snapshot with transient-local QoS plus an explicit fetch path. The gateway cannot decide correctness or increment attempts. Browser refresh reconnects to current backend state.

`ExecutePickPlace` carries cube identity, grid cell, destination identity and relevant round/config/calibration revisions. Feedback follows the spec's planning/pregrasp/descent/grasp/lift/destination/release/retreat stages. Results separate operation success from structured execution errors; motion never decides correct/wrong. Exact new message/service schemas should be finalized with their consuming phase, not invented as existing hardware contracts.

## 5. UI gateway and frontend

Use FastAPI HTTP/WebSocket transport and an `rclpy` adapter with clearly separated ROS spinning and web event handling. The gateway exposes allowlisted application intents and state snapshots, not arbitrary ROS topics, controller actions or gripper register commands. Separate kid/operator routes and permissions; an operator page URL alone is not an authorization boundary.

The Kid UI uses only central Croatian resources, including missing-translation checks with no English fallback. Large dynamic answer buttons, configurable attempt indicators, cube symbols in addition to color and immediate input lockout are required. Coordinate answers come from backend snapshots, not duplicated frontend math. The Operator UI provides setup confirmation, readiness, diagnostics, calibration/teaching and deliberate recovery controls. Application Home/Abort is not an emergency stop or an automatic robot-home command.

Do not generate the frontend in Phase 2. Later add declared/pinned web and gateway dependencies to the existing Docker workflow while preserving root/privileged/GPU/host-network decisions. With host networking, choose an explicit listen address/port; do not assume Docker port mapping provides isolation.

## 6. Mock and plan-only execution

**Application mock:** `mock_execution: true` selects a synthetic action server with configurable timing, feedback, cancellation and injected failures. It loads no UR/Modbus clients, starts no hardware bringup and sends no gripper initialization command. The full game/UI works with explicitly synthetic calibration, teaching and cell-readiness fixtures; these cannot make real mode ready. This is separate from both UR `use_mock_hardware` and Gazebo.

**Plan-only:** `plan_only: true` uses the authoritative model and application scene/policy but exposes no trajectory-execution or gripper-command path. It plans against a selected offline state fixture or explicitly authorized passive state input. Hypothetical gripper/object attachment changes remain in its planning scene; they are not physical state reports. Returning a validated plan does not mark a real cube removed or deliver a reward. Reject contradictory execution flags rather than silently enabling a stronger mode.

Future ROS integration tests use a separate domain, localhost discovery and fake namespaces. The audit sandbox denied sockets, so loopback/DDS tests need a suitable isolated environment for full verification. Gazebo is optional later integration coverage, not a dependency of pure game/mock tests.

## 7. Calibration and wrapping existing motion

Calibration captures actual current joints/TF, computes the configured pen tip in `base_link`, validates board side lengths/orthogonality and optional PXY, and accepts only right-handed orthonormal transforms. Publish `base_link` → `grid_frame`; publish a right-handed rotated `game_origin_frame`. Store missing/invalid data as not ready. The gripper fitting GUI cannot supply `tool_to_pen_tip`.

Retain MoveIt's `world` planning frame, `ur_manipulator` group and `tool0` endpoint. Convert calibrated board targets explicitly. For a future commissioned task TCP:

```text
T_world_tool0_target = T_world_task_tcp_target * inverse(T_tool0_task_tcp)
```

Do not assume the existing tactile-reference `grasp_tcp` is the cube TCP. Capture/validate its replacement or application offset during commissioning; do not change the SRDF endpoint merely to make a plan pass. Taught home/safe are actual captured joint states, not copies of SRDF `home`.

Later, `robots_and_cubes_motion` uses MoveIt C++ planning/execution APIs and the existing scaled controller mapping. Phase 7 should add a reviewed, opt-in application pipeline profile to the existing MoveIt integration, enabling installed Pilz `CommandPlanner` with commissioned Cartesian/joint limits. Normal workcell defaults remain unchanged. Use explicit PTP transit and LIN descent/lift/release. Phase 9 requests existing `RRTstarkConfigDefault` in `ompl` only for suitable free-space fallback; never replace required LIN segments with arbitrary sampling paths.

Before every execution, validate successful/nonempty plans, approved joint bounds, wraparound/excursion, collision state, orientation, board clearance and proximity to fresh current state. Preflight every selectable cube before unlocking Kid Mode. Revalidate changed scenes/states rather than executing a stale preflight plan.

The gripper adapter wraps `/robotiq_3f/activate`, `/robotiq_3f/gripper_command`, `/robotiq_3f/stop` and `/robotiq_3f/status`, using native `/robotiq_3f/move` only if commissioning requires it. Expose initialize/open/close-for-cube/stop/status; initialization is an explicit operator request, never startup behavior. Action cancellation and stop have distinct semantics; monitor both outcomes. A successful stalled result means contact, not proven possession. Cube-specific close effort/gap and reliable detection remain commissioning tasks.

Application scene ownership covers board, origin, cubes, destinations and fixed task obstacles, reusing the existing table. Attach/detach cubes only at confirmed stages, with narrowly reviewed touch links. Keep planned versus physical object state distinct through errors and recovery. Never automatically reset protective stops or robot safety systems.

## 8. Conflicts and decisions requiring later validation

| Finding | Planned treatment |
|---|---|
| RRT* is current primary; spec wants Pilz primary | Opt-in application planning profile in Phase 7; fallback in Phase 9 |
| `world`, `base_link`, `base` differ | Explicit TF conversion and frame-tagged models; no frame renaming |
| Current TCP is tactile-reference; pen/cube TCP unknown | Required commissioning fields, unset until measured |
| Existing mock switch leaves peripherals enabled | New application mock with no hardware includes or command clients |
| Default 90 mm pitch / 60 mm cubes leave 30 mm gaps | Do not certify adjacency; commission with actual gripper or disable adjacent layouts |
| Reachable reward placement versus safe child retrieval | Commission a delivery/access arrangement; prompt retrieval only after release/retreat and safe access conditions |
| Beginner success destination unspecified | Make destination policy explicit before motion integration; never infer correctness from color |
| Existing collision matrix/model home versus game safety | Validate game scene, touch links, taught poses and trajectory policy independently |
| Runtime persistence absent | Use existing project bind mount with explicit config/data/log paths and revisioned schemas |
| Stale README / baseline test failures | Record audit baseline; repair documentation/lint separately when scoped, not by changing hardware settings |

## 9. Phases and review gates

| Phase | Scope and verification |
|---|---|
| 1 — this change | Inventory and plan only; audit review before further work |
| 2 — complete | `user_settings.yaml`, `robot_commissioning.yaml`, strict typed loading, board/cube models, exact coordinate math, mode definitions, seeded round generator and hardware-independent state machine |
| 3 | Remaining application contracts and game ROS boundary; runtime persistence schemas and documentation will be scoped during review |
| 4 | Grid calibration and teaching; synthetic translated/rotated/noisy/invalid board tests, persistence/invalidation; no automatic robot jogging |
| 5 | Mock action executor; full game loop, stage failures, cancellation, idempotent recovery |
| 6 | Croatian Kid UI + Operator UI/gateway; dynamic answers, localization, lockout, reconnect, setup/calibration/teaching screens |
| 7 | Opt-in Pilz motion and trajectory policy; offline/plan-only checks before supervised execution |
| 8 | Full scene and gripper integration; attach/detach, contact/stop/cancel, partial-operation recovery |
| 9 | Existing RRT* ID used for validated free-space fallback only |
| 10 | Explicitly supervised physical commissioning: calibration, all cells, grasp geometry, speed/joint policy, adjacency, destinations and recovery |
| 11 | Exhibition usability, persistence/restart tests, operator/troubleshooting guides and polish |

## 10. Phase 2 delivery boundary

Implemented under `ur5_ws/src/labus/robots_and_cubes/`:

- `robots_and_cubes_config`: strict immutable configuration models and loaders;
- `robots_and_cubes_game`: pure board/cube models, exact coordinate transforms,
  seeded bounded generation, mode rules, and explicit game state transitions;
- root `config/user_settings.yaml` and `config/robot_commissioning.yaml`.

This phase deliberately contains no ROS node, frontend, runtime calibration,
MoveIt profile, driver/gripper client, or execution path. Further work requires
the next reviewed scope.
