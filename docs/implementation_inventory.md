# Robots and Cubes — Phase 1 Implementation Inventory

Audit date: 2026-09-11. `AGENTS.md` and all 104 numbered specification sections were read before inspection. No hardware launch/command, game implementation, robot behavior change, or MoveIt configuration change was performed. Findings describe checked-out source and installed dependencies, not a queried live robot. Historical hardware validation in README files is not new validation by this audit.

Paths are repository-relative unless absolute. Package-relative paths below resolve against the exact source directories in the package table.

## 1. Repository and package inventory

Colcon discovers **19 packages**; three additional manifests are excluded by `COLCON_IGNORE`. The `ur5_workcell/` subsystem directories are grouping directories, not ROS packages.

| Package | Exact source directory | Responsibility/status |
|---|---|---|
| `ur5_workcell_description` | `ur5_ws/src/ur5_workcell/descriptions/ur5_workcell_description` | Authoritative calibrated assembly |
| `ur5_workcell_bringup` | `ur5_ws/src/ur5_workcell/bringup/ur5_workcell_bringup` | Official UR and peripheral orchestration |
| `ur5_workcell_moveit_config` | `ur5_ws/src/ur5_workcell/moveit/ur5_workcell_moveit_config` | SRDF, OMPL, KDL, execution mappings |
| `ur5_workcell_sim` | `ur5_ws/src/ur5_workcell/simulation/ur5_workcell_sim` | Gazebo, arm/gripper control, RGB-D bridges |
| `robotiq_3f_description` | `ur5_ws/src/ur5_workcell/robotiq_3f/robotiq_3f_description` | Articulated/fixed AGS geometry |
| `robotiq_3f_interfaces` | `ur5_ws/src/ur5_workcell/robotiq_3f/robotiq_3f_interfaces` | Native messages and Move action |
| `robotiq_3f_driver` | `ur5_ws/src/ur5_workcell/robotiq_3f/robotiq_3f_driver` | C++ Modbus TCP backend |
| `robotiq_3f_controller` | `ur5_ws/src/ur5_workcell/robotiq_3f/robotiq_3f_controller` | Backend-neutral services/actions |
| `robotiq_3f_state_publisher` | `ur5_ws/src/ur5_workcell/robotiq_3f/robotiq_3f_state_publisher` | Actual-feedback joint mapping |
| `robotiq_3f_calibration` | `ur5_ws/src/ur5_workcell/robotiq_3f/robotiq_3f_calibration` | Python/Qt gripper fitting, not board calibration |
| `robotiq_ft300s_description` | `ur5_ws/src/ur5_workcell/robotiq_ft/robotiq_ft300s_description` | FT geometry/measurement frame |
| `robotiq_ft_streamer` | `ur5_ws/src/ur5_workcell/robotiq_ft/robotiq_ft_streamer` | TCP FT stream/software zero |
| `realsense_l515_description` | `ur5_ws/src/ur5_workcell/realsense_l515/realsense_l515_description` | Mounted camera geometry |
| `xela_usp44_description` | `ur5_ws/src/ur5_workcell/xela_usp44/xela_usp44_description` | Tactile geometry |
| `ur5_robotiq` | `ur5_ws/src/ur5_robotiq` | Legacy description/simulation scaffold |
| `ur5_robotiq_moveit_config` | `ur5_ws/src/ur5_robotiq_moveit_config` | Legacy MoveIt/Servo configuration |
| `robotiq_description` | `ur5_ws/src/ros2_robotiq/robotiq_description` | Copied legacy assets |
| `robotiq_ft_sensor_interfaces` | `ur5_ws/src/ros2_robotiq/robotiq_ft_sensor_interfaces` | Legacy FT messages/services |
| `robotiq_ft_sensor_hardware` | `ur5_ws/src/ros2_robotiq/robotiq_ft_sensor_hardware` | Built serial FT driver; not active TCP installation |
| `robotiq_driver` | `ur5_ws/src/ros2_robotiq/robotiq_driver` | Ignored copied 2F driver; unsuitable for 3F |
| `robotiq_controllers` | `ur5_ws/src/ros2_robotiq/robotiq_controllers` | Ignored copied controller |
| `robotiq_hardware_tests` | `ur5_ws/src/ros2_robotiq/robotiq_hardware_tests` | Ignored hardware executables |

External packages reside in `/opt/ros/jazzy`, including `ur_robot_driver`, `ur_description`, `ur_controllers`, `ur_client_library`, MoveIt, `gz_ros2_control`, and `ros_gz_*`. RealSense uses `/opt/realsense_ws/install`. These drivers are not repository-owned implementations.

Other structure:

- `docker/`: image, build/run scripts, camera compatibility patches.
- Package `test/`, `launch/`, `config/`, `urdf/`, `meshes/`, `rviz/`, `worlds/`: tests, orchestration, parameters, and assets.
- `ur5_ws/models/`: ignored peg/hole STL and Blender assets.
- `gripper_calibration/gripper_samples.csv`: physical gripper fitting samples.
- `ur5_ws/build/`, `install/`, `log/`: pre-existing generated artifacts.
- `docs/treasure_hunt_spec.md`: requested application specification.
- `ur5_ws/src/labus/robots_and_cubes/`: reserved Robots and Cubes application root; currently contains only its organizational README and is not a ROS package.

No Robots and Cubes packages, game core, board calibration, taught-position manager, browser frontend, or UI gateway exist. The gripper Qt fitting GUI and simulated backend are relevant existing tools, not an existing game application.

## 2. Robot, frames, and TCP

| Item | Discovered value | Evidence |
|---|---|---|
| Robot | **UR5**, not UR5e | Bringup `config/hardware.yaml`; `launch/hardware.launch.py` permits only `ur5` |
| ROS / OS target | **Jazzy / Ubuntu 24.04** | `docker/Dockerfile`; installed `/opt/ros/jazzy/setup.bash` |
| ROS robot base | **`base_link`**, empty default `tf_prefix` | Description wrappers and SRDF |
| Controller-coordinate base | `base`, yaw pi from `base_link` | `/opt/ros/jazzy/share/ur_description/urdf/ur_macro.xacro` |
| MoveIt planning/model frame | **`world`** | Offline `moveit::core::RobotModel::getModelFrame()` on expanded authoritative URDF/SRDF |
| Application task reference | **`base_link`** (user-approved after audit) | `config/robot_commissioning.yaml` |
| Planning group | **`ur_manipulator`** | MoveIt `config/ur5_workcell.srdf` |
| Planning chain / endpoint | `base_link` → **`tool0`**, six arm joints | Same SRDF; no declared SRDF end-effector group |
| Description TCP | **`grasp_tcp`**, fixed child of `tool0` | Description `urdf/ur5_workcell_macro.xacro` |
| Pendant-selected TCP | **Unknown offline** | Official broadcaster config describes `base` → `tool0_controller`; no current pendant TCP recorded |
| Application cube TCP | **`cube_grasp_tcp`**, `tool0` translation `[0, 0, 0.275]` m, reviewed tooling orientation retained | User-approved after audit; `config/robot_commissioning.yaml` |
| Calibration pen | `tool0` tip translation **`[0, 0, 0.315]` m**; sampled points stored in `base_link` | User-approved after audit; `config/robot_commissioning.yaml` |

`tool0` → reusable `grasp_tcp`: xyz `[-0.05091168824543142, 0.05091168824543142, 0.275]` m; rpy `[0, 0, -0.7853981633974483]` rad. The source identifies a Basic/open tactile outer-edge reference and remains unchanged. The application-specific `cube_grasp_tcp` instead uses zero X/Y and the approved 0.275 m Z while retaining that reviewed orientation in application configuration. `tool0` is UR's all-zero tool frame; neither application setting establishes the pendant-selected TCP.

Current wrappers use `world` → `workcell_reference` (identity) → `base_link` (yaw pi). The table attaches to `workcell_reference`: size 0.9 × 1.5 × 0.9 m, center `[0, -0.54, -0.45]` m in that frame; mounting-edge offset 0.21 m. Those table coordinates must not be treated as `base_link` coordinates. Expanded default description: **50 links, 49 joints, 17 movable joints** (six arm, eleven gripper).

Authoritative files under `ur5_ws/src/ur5_workcell/descriptions/ur5_workcell_description/`:

- `urdf/workcell.urdf.xacro`: standalone geometry.
- `urdf/workcell_control.urdf.xacro`: same assembly plus official UR control system.
- `urdf/ur5_workcell_macro.xacro`: reusable assembly, TCP, camera/tactile mounts.
- `urdf/ur5_tooling.xacro`: FT/coupler/gripper chain.
- `urdf/workcell_environment.xacro`: table collision volume.
- `config/camera_extrinsics.yaml`: camera mount provenance, not grid calibration.

## 3. Factory calibration and driver startup

Robot-specific kinematics are configured in `ur5_ws/src/ur5_workcell/descriptions/ur5_workcell_description/config/ur5_calibration.yaml`, hash **`calib_16683543926985068857`**. Bringup's `kinematics_params_file` defaults to this file; both description wrappers use it, and the official control macro loads its hash. Sibling `ur5_calibration.generated.yaml` exists but is not the selected default. Configuration is verified; matching a connected robot remains a runtime check. README reports prior successful matching.

Existing startup workflow, documented but **not executed during this audit**:

```bash
./docker/build_docker.sh
./docker/run_docker.sh
# Inside the container:
cd /workspaces/ur5_ros2/ur5_ws
source /opt/ros/jazzy/setup.bash
source /opt/realsense_ws/install/local_setup.bash
colcon build --symlink-install
source install/local_setup.bash
ros2 launch ur5_workcell_bringup hardware.launch.py launch_rviz:=false launch_moveit:=true
```

`ur5_workcell_bringup/launch/hardware.launch.py` includes `/opt/ros/jazzy/share/ur_robot_driver/launch/ur_control.launch.py`, using `ur_rsp.launch.py`, official controller configuration/RTDE recipes and the workcell control xacro. Robot IP: `192.168.88.245`; reverse IP default: `0.0.0.0`. Reverse/script-sender/trajectory/script-command ports: 50001/50002/50003/50004. UR5 update rate: 125 Hz, from `/opt/ros/jazzy/share/ur_robot_driver/config/ur5_update_rate.yaml`.

Headless mode, dashboard launch, and tool communication are false. The documented handshake requires running the pendant External Control program. Its current contents, host reverse-connection address and robot readiness were not inspected. Launch activates the selected trajectory controller but sends no trajectory. Gripper connects without activation/motion; FT startup zero is false. Camera, gripper, FT and general RViz default on; MoveIt defaults off. The example explicitly opts into MoveIt.

Other entry points (relative to package directories above):

- `robotiq_3f_controller/launch/hardware.launch.py`: standalone gripper stack.
- `robotiq_3f_driver/launch/driver.launch.py`: backend only.
- `robotiq_3f_state_publisher/launch/joint_states.launch.py`: non-commanding mapper.
- `robotiq_ft_streamer/launch/ft_streamer.launch.py`: external FT.
- `ur5_workcell_description/launch/view_description.launch.py`: geometry-only RViz.
- `robotiq_3f_calibration/launch/calibration.launch.py`: gripper fitting.
- Legacy `ur5_robotiq/launch/ur5_robot_sim_moveit.launch.py`, `ur5_sim_control.launch.py`, `ur5_robotiq_view.launch.py`; legacy MoveIt has generated demo, MoveGroup, RViz, controller-spawn, warehouse, and Servo-capable launch files. These are not the authoritative entry points.

## 4. MoveIt, planners, and controllers

Files under `ur5_ws/src/ur5_workcell/moveit/ur5_workcell_moveit_config/`:

| File | Configuration |
|---|---|
| `launch/moveit.launch.py` | MoveGroup/RViz for existing bringup; explicitly `pipelines=['ompl']`, default `ompl` |
| `.setup_assistant` | Resolves authoritative `workcell.urdf.xacro` |
| `config/ur5_workcell.srdf` | `ur_manipulator`, `tool0`, named `home`, collision exclusions |
| `config/kinematics.yaml` | `kdl_kinematics_plugin/KDLKinematicsPlugin`, resolution 0.005, timeout 0.05 s |
| `config/ompl_planning.yaml` | `ompl_interface/OMPLPlanner`; **`RRTstarkConfigDefault`** (`geometric::RRTstar`) is group default; `RRTConnectkConfigDefault` also available |
| `config/joint_limits.yaml` | Velocity/acceleration scaling 0.1; supplemental acceleration limits 5.0 rad/s² |
| `config/moveit_controllers.yaml` | Simple controller manager, scaled/default and unscaled action mappings; execution-duration monitoring false |
| `config/moveit.rviz` | RViz fixed frame `world` |

**Pilz is installed, but not enabled in the authoritative stack.** `/opt/ros/jazzy/share/pilz_industrial_motion_planner/package.xml` reports 2.12.4; its `plugins/pilz_industrial_motion_planner_plugin_description.xml` registers `pilz_industrial_motion_planner/CommandPlanner`. No authoritative Pilz Cartesian limits exist.

Legacy `ur5_ws/src/ur5_robotiq_moveit_config/config/pilz_cartesian_limits.yaml` exists. Its automatic MoveIt builder resolves `stomp`, `ompl`, `pilz_industrial_motion_planner`, and `chomp` from installed defaults, verified without starting nodes. These are not enabled by authoritative bringup, nor were they tested for planning. Legacy limits are not commissioned game limits.

Arm joints: `shoulder_pan_joint`, `shoulder_lift_joint`, `elbow_joint`, `wrist_1_joint`, `wrist_2_joint`, `wrist_3_joint`.

| Controller/interface | Configured purpose |
|---|---|
| `scaled_joint_trajectory_controller` | Default active arm controller; `/scaled_joint_trajectory_controller/follow_joint_trajectory`, `control_msgs/action/FollowJointTrajectory` |
| `joint_trajectory_controller` | Alternative action at `/joint_trajectory_controller/follow_joint_trajectory`; initially inactive |
| `joint_state_broadcaster` | Arm `/joint_states`, `sensor_msgs/msg/JointState` |
| `io_and_status_controller` | UR IO, robot/safety/program state |
| `speed_scaling_state_broadcaster` | Speed scaling |
| `force_torque_sensor_broadcaster` | Official UR FT, separate from external Robotiq FT |
| `tcp_pose_broadcaster` | Controller TCP in `base`, child `tool0_controller` |
| `ur_configuration_controller`, `friction_model_controller` | Additional active selections in installed official launch |

Installed configuration: `/opt/ros/jazzy/share/ur_robot_driver/config/ur_controllers.yaml`. Other initially inactive controllers: `forward_velocity_controller`, `forward_position_controller`, `forward_effort_controller`, `force_mode_controller`, `passthrough_trajectory_controller`, `freedrive_mode_controller`, `tool_contact_controller`. These are startup declarations, not live activation observations or proof of CB-series feature support.

Simulation files under `ur5_ws/src/ur5_workcell/simulation/ur5_workcell_sim/`: `launch/sim.launch.py`, `urdf/workcell_sim.urdf.xacro`, `worlds/workcell.sdf`, `config/ur_controllers.yaml`. Gazebo/Bullet Featherstone uses 250 Hz and starts `joint_state_broadcaster`, `scaled_joint_trajectory_controller`, and `robotiq_3f_position_controller` together. `scripts/robotiq_3f_sim_backend.py` implements native gripper status/command behavior and commands eleven simulated joints. It synthesizes raw feedback, without reliable physical contact/retention simulation. This is articulated simulation, not the old fixed-gripper baseline. `config/camera_bridge.yaml` and `urdf/l515_sim.xacro` provide RGB-D topics. Gazebo was not launched.

## 5. Gripper and sensor interfaces

These identifiers come from controller/driver source and the `robotiq_3f` launch namespace.

| Endpoint | ROS type | Role |
|---|---|---|
| `/robotiq_3f/gripper_command` | `control_msgs/action/GripperCommand` | Physical-gap Pinch action |
| `/robotiq_3f/move` | `robotiq_3f_interfaces/action/Move` | Native modes and independent A/B/C/S motion |
| `/robotiq_3f/activate` | `std_srvs/srv/Trigger` | Explicit reset/activation; may move fingers |
| `/robotiq_3f/deactivate` | `std_srvs/srv/Trigger` | Explicit deactivation |
| `/robotiq_3f/stop` | `std_srvs/srv/Trigger` | Stop; does not itself cancel an active action |
| `/robotiq_3f/status` | `robotiq_3f_interfaces/msg/Robotiq3FStatus` | Public feedback/transport health |
| `/robotiq_3f/backend/command` | `robotiq_3f_interfaces/msg/Robotiq3FCommand` | Internal controller/backend contract, not UI API |
| `/robotiq_3f/backend/status` | `robotiq_3f_interfaces/msg/Robotiq3FStatus` | Internal feedback |
| `/joint_states` | `sensor_msgs/msg/JointState` | Mapper output alongside arm states |

Definitions are in `robotiq_3f_interfaces/action/Move.action`, `msg/Robotiq3FCommand.msg`, `msg/Robotiq3FStatus.msg`. Implementations: controller `src/controller_node.cpp`, driver `src/driver_node.cpp`, mapper `src/joint_state_publisher_node.cpp`.

Status includes timestamps, connection/command IDs, activation/initialization, mode, motion state, A/B/C/S contact statuses, fault code, requested/actual raw positions, currents and diagnostics. Public QoS is reliable depth 10, not transient-local. The application must enforce freshness; mapper reference/held poses are not readiness evidence.

Pinch conversion: 0.155 m → raw 0, 0.0775 m → 56, 0 m → 112. Effort: 15–60 N per finger, zero selects 30 N; native speed 20. Feedback uses actual A with gap clamping. Effort feedback is zero because raw current is not measured force. Partial/all contact maps to `stalled`, reached maps to `reached_goal`; contact may complete successfully without reaching the target. These semantics do not prove retention of a game cube.

Configuration: controller `config/controller.yaml`, driver `config/driver.yaml`, mapper `config/joint_mapping.yaml`, bringup `config/hardware.yaml`. Active Modbus defaults: `192.168.88.237:502`, unit 0, 10 Hz. Native/standard actions share an operation lock; cancellation/timeout sends stop; reconnect does not replay motion. Automatic release is disabled. Use exactly one gripper command owner.

External FT: `/robotiq_ft_sensor/wrench` (`geometry_msgs/msg/WrenchStamped`), `ft_measurement_frame`, TCP `192.168.88.245:63351`; `/robotiq_ft_streamer/zero` (`std_srvs/srv/Trigger`). Configuration: `robotiq_ft_streamer/config/ft_streamer.yaml`.

Camera: `/camera/camera`; `/camera/color/image_raw`, `/camera/depth/image_rect_raw`, `/camera/aligned_depth_to_color/image_raw` and CameraInfo at 640×480/30 Hz. Optional `/camera/depth/color/points` defaults off. Description owns `tool0` → `camera_link`; wrapper owns downstream optical TF. XELA has geometry but no authoritative tactile runtime driver. V1 manual setup does not require perception.

## 6. Docker and persistent storage

- `docker/Dockerfile`: NVIDIA CUDA 12.8/cuDNN Ubuntu 24.04, Jazzy desktop/UR/MoveIt/Gazebo, pinned librealsense 2.54.2 RSUSB and RealSense ROS 4.54.1; patches in `docker/patches/`. Workspace is not built into the image.
- `docker/build_docker.sh`: builds `ur5_ros2:latest`; image/tag/camera versions overridable.
- `docker/run_docker.sh`: requires legacy directory `/home/robot/projects/ur5-door-interaction` (overridable), removes existing `ur5_ros2_dev`, and creates an interactive root/privileged container with host networking, GPUs, X11, USB, Vulkan, private 10 GB shared memory, rtprio 99 and unlimited memlock. Running it during an audit could remove a working container; it was not run.
- Bind mounts: script-derived project root → `/workspaces/ur5_ros2` (`CONTAINER_WS` override); legacy project → `/opt/reference/ur5-door-interaction` read-only. Files under the project mount persist on the host; container-only files do not survive replacement.
- Interactive `.bashrc` sources Jazzy, camera overlay and existing workspace `local_setup.bash` at the default image path. Custom `CONTAINER_WS` requires explicit sourcing because that path is fixed.
- ROS defaults: domain 0, `rmw_fastrtps_cpp`, discovery `SUBNET`; CycloneDDS installed. No Compose/application named volume/web service exists. Host networking means a future gateway binds a host port, not a Docker-published port.
- Config/calibration/teaching/log directories under the project mount can persist without rebuild. A game runtime-data policy does not exist in `.gitignore`; it currently ignores build/install/log/model caches and `AGENTS.md`. Node/npm were not found on the audit PATH; frontend dependencies are not explicitly provisioned by the Dockerfile.

## 7. Offline checks and limitations

Fresh build/install/test artifacts were isolated in `/tmp/treasure_audit`. Initial colcon discovery could not create repository-root `log`; specifying a temporary log base resolved that filesystem issue. Existing workspace build/install artifacts were not replaced.

Commands run from the repository root:

```bash
source /opt/ros/jazzy/setup.bash
source /opt/realsense_ws/install/local_setup.bash
colcon --log-base /tmp/treasure_audit/log build \
  --base-paths "$PWD/ur5_ws/src" --build-base /tmp/treasure_audit/build \
  --install-base /tmp/treasure_audit/install --symlink-install \
  --parallel-workers 2 --cmake-args -DBUILD_TESTING=ON
source /tmp/treasure_audit/install/local_setup.bash
export ROS_DOMAIN_ID=173 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export ROS_LOG_DIR=/tmp/treasure_audit/ros_logs PYTHONDONTWRITEBYTECODE=1
colcon --log-base /tmp/treasure_audit/test_logs test \
  --base-paths "$PWD/ur5_ws/src" --build-base /tmp/treasure_audit/build \
  --install-base /tmp/treasure_audit/install --executor sequential \
  --return-code-on-test-failure
colcon --log-base /tmp/treasure_audit/results_log test-result \
  --test-result-base /tmp/treasure_audit/build --verbose
```

| Check | Result |
|---|---|
| Fresh build | **19 packages built**; legacy FT package emits deprecated API warnings |
| Python AST parsing | **57 files passed** |
| XML/xacro/URDF/SRDF/SDF parsing | **73 files passed** |
| YAML safe loading | **24 files passed**; syntax only, not a game schema |
| `bash -n docker/build_docker.sh docker/run_docker.sh` | Passed |
| Xacro expansion and `check_urdf` | Passed, root `world` |
| Offline C++ MoveIt model construction | `MODEL_FRAME=world`, `ROOT_LINK=world`, `GROUP=ur_manipulator`; no end-effectors. No ROS node initialized; logger warning did not prevent inspection |
| Description / bringup / MoveIt / simulation tests | **10 / 2 / 4 / 3 passed** |
| Gripper protocol / joint mapping | **3 / 6 passed** |
| Gripper calibration tests | **10 passed** |
| FT suite | **8 passed, 2 failing/blocked** by denied loopback socket creation |
| Modbus loopback test | Failing/blocked: socket `Operation not permitted` |
| Controller fake-backend test | DDS socket/interface enumeration denied; discovery fails and launch times out, producing missing-result error. Only `/test_robotiq_3f` controller/fake backend involved |
| Legacy `ur5_robotiq` | flake8 fails with **213 existing style errors/warnings**; copyright skipped |

Raw colcon aggregation: **127 tests, 1 error, 6 failures, 13 skipped**. This includes CTest wrappers and nested results, not 127 independent behavior cases. Twelve skips are cppcheck checks; one is legacy copyright. Output is in `/tmp/treasure_audit/test_results.txt` and `tests_console.txt`; those temporary artifacts are not deployment data. Socket failures are environmental, not evidence of hardware faults. Tests/configuration were not changed to hide them. Docker rebuild, live MoveGroup planning, Gazebo execution and physical validation were not performed.

## 8. Conflicts, gaps, and unknowns

1. **Planner policy:** spec wants primary Pilz PTP/LIN and RRT* fallback; authoritative configuration currently makes OMPL/RRT* primary. Resolve later in Phase 7; preserve normal workcell defaults.
2. **Frames:** `base_link` is the authoritative application frame, while MoveIt uses `world` and controller coordinates use `base`. The future motion wrapper must perform explicit transforms and reject untagged/mixed-frame Cartesian data.
3. **TCP:** application cube and pen translations are resolved in `robot_commissioning.yaml`. The reusable tactile `grasp_tcp` stays unchanged. Pendant-selected TCP, board-relative grasp height, separately commissioned orientation changes, cube-specific opening/force/retention and edge yaw remain unknown.
4. **Missing application:** configuration tiers, schemas, game/UI, board scene, calibration/teaching/log persistence, preflight, trajectory policy and application mock/plan-only modes do not exist. `use_mock_hardware` only mocks UR; default gripper/FT/camera may still connect unless explicitly disabled.
5. **Physical commissioning:** board placement/thickness, origin geometry, destinations, taught safe/home, cell reachability, adjacency clearance, approved joint/excursion limits and exhibition speeds are unknown. SRDF `home` is a model state, not an operator-taught safe game pose. Existing collision exclusions do not certify grasp/contact safety.
6. **Spec ambiguities:** user-level default yaw overlaps advanced yaw/cell files; precedence needs definition. Reward placement must be robot-reachable while retrieval must be outside the active area after retreat. Beginner correctness is color-independent, but correct-cube destination is not explicit. None requires inventing physical values in Phase 2.
7. **Documentation drift:** root README still describes a fixed simulated gripper and contains an inactive-controller statement contradicted by source. Subsystem overview labels existing camera/MoveIt/simulation work as future work. Current source/tests take precedence; these files were not changed.
8. **Live unknowns:** current controller activation, safety/program state, connected factory-calibration match, External Control settings, hardware connectivity, camera identity and real gripper reliability were not queried.

See [implementation_plan.md](implementation_plan.md). Phase 2 must wait for audit review.
