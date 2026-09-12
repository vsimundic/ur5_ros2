# Robots and Cubes UI gateway

Phase 6 adds a browser-only application boundary. It is deliberately not a
robot-control server.

```text
React Kid / Operator UI
        |
  HTTP + WebSocket DTOs
        |
FastAPI transport / snapshot relay
        |
thread-confined rclpy application bridge
        |
game manager + command-free calibration/teaching services
```

The bridge owns all rclpy clients, subscriptions, executor spinning and
destruction on one private thread. FastAPI work submits only named,
allowlisted requests to that thread. It cannot expose arbitrary ROS services,
topics, actions, parameters, drivers, controllers, or robot hardware details.
`ExecutePickPlace` remains the only long-running operation and is still owned
by the game manager/action-server pair.

## Browser API

`GET /api/state` and WebSocket `/api/ws` deliver complete versioned snapshots.
The first WebSocket message is always a complete snapshot; later messages have
a newer `version`. A reconnect fetches the current backend snapshot and never
generates a round or replays state history.

State-changing routes require a browser-created `request_id` and pass it, plus
round/operation identity when required, unchanged to the existing application
services:

- `POST /api/rounds`
- `POST /api/rounds/confirm-setup`
- `POST /api/rounds/selections`
- `POST /api/operations/retry`
- `POST /api/operations/reconcile`
- `POST /api/rounds/abort`

The calibration and teaching routes mirror only the existing command-free
application contracts. They capture measured state through their existing
adapter; they never jog, home, plan, execute, or command a gripper.

## Mock UI development

Build the React project after the normal Docker image has been rebuilt (it now
includes Node/npm and FastAPI/Uvicorn):

```bash
cd /workspaces/ur5_ros2/ur5_ws/src/labus/robots_and_cubes/web/robots_and_cubes_web
npm install
npm run build
```

Then launch the mock-only backend and gateway. This starts no UR, MoveIt,
controller, Modbus, gripper, camera, or hardware network client:

```bash
export ROBOTS_AND_CUBES_OPERATOR_TOKEN="$(openssl rand -hex 32)"
ros2 launch robots_and_cubes_bringup mock_game.launch.py \
  user_settings_path:=/workspaces/ur5_ros2/ur5_ws/src/labus/robots_and_cubes/config/user_settings.yaml \
  child_text_path:=/workspaces/ur5_ros2/ur5_ws/src/labus/robots_and_cubes/config/child_text_hr.yaml \
  event_log_path:=/tmp/robots_and_cubes_mock_events.jsonl \
  web_dist_path:=/workspaces/ur5_ros2/ur5_ws/src/labus/robots_and_cubes/web/robots_and_cubes_web/dist
```

Open `http://127.0.0.1:8080/kid` or `/operator`. For frontend development,
use `npm run dev`; Vite proxies `/api` and the WebSocket to the local gateway.
The default bind address is loopback. A supervised LAN display requires the
explicit `gateway_host:=0.0.0.0` launch argument; a route is not an access
control boundary.

All Kid Mode copy is central UTF-8 data in `config/child_text_hr.yaml`. The
gateway rejects missing keys at startup and the frontend does not provide an
English fallback.

## Operator authorization

Every operator-only HTTP intent requires `Authorization: Bearer <token>`. The
gateway reads the token only from runtime environment variable
`ROBOTS_AND_CUBES_OPERATOR_TOKEN` (or the selected `operator_token_env`); no
secret is committed. The `/operator` page holds a supplied token only in memory.
Kid selection, public state, Kid copy, and the read-only snapshot WebSocket do
not grant any operator capability. The WebSocket accepts no commands.
