# Phase 6 manual UI test — normal Docker container

This is a mock-only browser procedure. It never starts a UR driver, MoveIt,
controller, gripper, camera, or physical robot motion.

## Validation record

The Phase 6 mock/browser flow was manually tested and accepted on 2026-09-12.
That acceptance is limited to the synthetic mock application and does not
authorize physical robot operation.

## Prepare

```bash
cd /workspaces/ur5_ros2/ur5_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-up-to robots_and_cubes_bringup
source install/setup.bash
export ROS_DOMAIN_ID=45
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export ROBOTS_AND_CUBES_OPERATOR_TOKEN="$(openssl rand -hex 32)"
cd src/labus/robots_and_cubes/web/robots_and_cubes_web
npm ci
npm run typecheck
npm run lint
npm test
npm run build
```

Expected: the ROS build succeeds; TypeScript, lint and Vitest succeed; `dist/`
contains `index.html` and `assets/`. Keep the token in this terminal only.

## Start the mock application

```bash
cd /workspaces/ur5_ros2/ur5_ws
ros2 launch robots_and_cubes_bringup mock_game.launch.py \
  user_settings_path:=/workspaces/ur5_ros2/ur5_ws/src/labus/robots_and_cubes/config/user_settings.yaml \
  child_text_path:=/workspaces/ur5_ros2/ur5_ws/src/labus/robots_and_cubes/config/child_text_hr.yaml \
  event_log_path:=/tmp/robots_and_cubes_mock_events.jsonl \
  web_dist_path:=/workspaces/ur5_ros2/ur5_ws/src/labus/robots_and_cubes/web/robots_and_cubes_web/dist
```

In another sourced terminal, run `ros2 node list`. Expected: only game manager,
mock `ExecutePickPlace` server, and UI gateway—not UR, MoveIt, Robotiq,
controller, Gazebo, or hardware nodes.

## Browser flow

1. Open `/operator`; enter `ROBOTS_AND_CUBES_OPERATOR_TOKEN`. Expected:
   authorization succeeds and the page says `SYNTHETIC MOCK MODE`.
2. Generate and confirm an **easy** round. Open `/kid`. Expected: five colour
   cubes on clickable board cells, a randomly selected Croatian target colour
   in neutral text, no separate answer buttons, and no origin.
3. Generate and confirm a **beginner** round. Expected: the green star, blue
   circle, red heart, black triangle, and white crescent on clickable board
   cells, a neutral Croatian target-shape word, no separate answer buttons, and
   no origin.
4. Generate and confirm a **spatial** round. Expected: the fixed origin, a
   relative-direction prompt such as `3 gore i 1 lijevo od ishodišta`, and
   shape answers.
5. Generate and confirm a **standard** round. Expected: an unrotated origin,
   the five shapes on the board, `(x, y)` answer buttons, and the green star as
   the target. Coordinates use a minus sign only for negative values (for
   example, `(2, -1)` and `(0, 3)`). Select its coordinate and expect one input
   lock, changing mock stages, then Croatian success.
6. Generate and confirm a **challenge** round. Expected: the configured origin
   rotation/handedness is drawn, any one of the five shapes is identified as
   the target, and the child chooses its `(x, y)` pair.
7. On a new Standard round choose a non-green coordinate. Expected: one
   completed synthetic operation consumes one attempt and disables that answer.
8. Refresh `/kid` during active motion, then `/operator`. Expected: both show
   the same round and neither creates a new one.
9. Optionally inject a mock failure as documented in [mock_execution.md](mock_execution.md).
   Expected: neutral Kid message and operator recovery controls.
10. Run `tail -n 20 /tmp/robots_and_cubes_mock_events.jsonl`. Expected: events
   retain the current round identity. Stop with `Ctrl-C`; no physical system is
   involved.
