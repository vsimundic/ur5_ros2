# UR5 workcell Gazebo simulation

This package spawns the authoritative UR5 workcell geometry in Gazebo Sim and
controls the six arm joints through `gz_ros2_control`. MoveIt and its RViz
interface start by default. Gazebo uses the Bullet Featherstone physics plugin
because the default DART plugin cannot construct collision shapes from all of
the installed tooling meshes. The robot mounting frame is rotated 180 degrees
relative to the world-fixed table and sits 0.21 m inboard from its short edge.
The arm starts with a zero shoulder-pan angle. A simulated L515 RGB-D camera
uses the promoted optical transform and starts by default.

Stop real-hardware bringup before starting the simulation. In particular, do
not let the real and simulated trajectory controllers share a ROS domain.

Build and launch from the workspace:

```bash
cd /workspaces/ur5_ros2/ur5_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-up-to ur5_workcell_sim
source install/setup.bash
ros2 launch ur5_workcell_sim sim.launch.py
```

The default launch opens Gazebo and MoveIt RViz. In RViz, select the
`ur_manipulator` planning group, choose or drag a goal for `tool0`, click
**Plan**, and then **Execute**. Useful checks in another sourced terminal are:

```bash
ros2 service call /controller_manager/list_controllers \
  controller_manager_msgs/srv/ListControllers '{}'
ros2 topic hz /joint_states
ros2 topic hz /clock
```

Both `joint_state_broadcaster` and
`scaled_joint_trajectory_controller` should be `active`; `/joint_states` and
`/clock` should publish continuously.

MoveIt starts only after both controller spawners have completed. This ensures
its initial planning state comes from the simulated robot's configured home
joint positions rather than a temporary all-zero state during startup.

The simulated camera publishes a registered 640 x 480 color/depth pair at
30 Hz using the real camera's topic convention:

```text
/camera/color/image_raw
/camera/color/camera_info
/camera/depth/image_rect_raw
/camera/depth/camera_info
/camera/aligned_depth_to_color/image_raw
/camera/aligned_depth_to_color/camera_info
```

View either image by adding an RViz Image display or by running:

```bash
ros2 run rqt_image_view rqt_image_view /camera/color/image_raw
```

## Simulated Robotiq 3F

Gazebo uses the authoritative articulated gripper and the same backend-neutral
controller API as the real device. Activate the simulated gripper once after
launch:

```bash
ros2 service call /robotiq_3f/activate std_srvs/srv/Trigger '{}'
```

Send Basic (`0`), Pinch (`1`), Wide (`2`), or Scissor (`3`) goals through the
native action. In Basic, Pinch, and Wide modes, `position_a` closes all three
fingers unless individual control is enabled. In Scissor mode it controls the
outer-finger separation:

```bash
ros2 action send_goal /robotiq_3f/move \
  robotiq_3f_interfaces/action/Move \
  "{mode: 0, position_a: 160, speed_a: 80, force_a: 80}"

ros2 action send_goal /robotiq_3f/move \
  robotiq_3f_interfaces/action/Move \
  "{mode: 1, position_a: 100, speed_a: 80, force_a: 80}"

ros2 action send_goal /robotiq_3f/move \
  robotiq_3f_interfaces/action/Move \
  "{mode: 2, position_a: 160, speed_a: 80, force_a: 80}"

ros2 action send_goal /robotiq_3f/move \
  robotiq_3f_interfaces/action/Move \
  "{mode: 3, position_a: 220, speed_a: 80, force_a: 80}"
```

Independent finger and scissor control are also available:

```bash
ros2 action send_goal /robotiq_3f/move \
  robotiq_3f_interfaces/action/Move \
  "{mode: 0, individual_finger_control: true, individual_scissor_control: true, position_a: 40, position_b: 100, position_c: 180, position_scissor: 160, speed_a: 80, speed_b: 80, speed_c: 80, speed_scissor: 80, force_a: 80, force_b: 80, force_c: 80, force_scissor: 80}"
```

The standard Pinch-mode `/robotiq_3f/gripper_command` action works unchanged.
The simulated backend currently models commanded free-space motion and mode
kinematics; native current sensing and contact-result semantics remain a
separate physics-validation step.

The state broadcaster, arm controller, and gripper controller activate as one
group so the simulated arm retains its configured startup pose. The startup
pose looks slightly above the table; plan the arm to a suitable
observation pose to inspect the workspace. The simulated color and depth
cameras are co-located, so the raw and aligned depth topics contain the same
registered depth image. The RGB near plane is close enough to render the
gripper fingers, while depth follows the L515's 0.25 m minimum range. To bridge
the generated point cloud as
`/camera/depth/color/points`, launch with `camera_pointcloud:=true`. Disable all
simulated camera output with `launch_camera:=false`.

For a headless smoke test:

```bash
ros2 launch ur5_workcell_sim sim.launch.py \
  gazebo_gui:=false launch_rviz:=false
```

The FT and tactile parts currently contribute geometry and collisions but do
not yet publish simulated sensor output.
