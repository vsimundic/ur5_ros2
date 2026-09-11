# robotiq_3f_calibration

ROS-native interactive fitting tool for the current articulated Robotiq 3F
description. It launches the gripper xacro in RViz and a Qt window that:

- publishes visualization-only joint states for all eleven gripper joints;
- exposes bidirectional degree sliders and exact numeric angle inputs so the
  Basic/open zero reference can be corrected in either direction;
- exposes X/Y/Z offset controls for the A/B/C proximal-to-middle rotation
  centers and shows those centers as colored markers in RViz;
- records mode, requested position, actual A/B/C/S feedback, joint angles,
  notes, measurement endpoints, and distances to CSV;
- reloads a saved CSV row into the complete visual pose and form, or duplicates
  it under a new sample ID for further adjustment;
- can follow an already-running `/robotiq_3f/status` publisher;
- pairs consecutive RViz `/clicked_point` selections and draws the endpoints,
  line, total distance, and signed B-minus-A `dx`, `dy`, and `dz`; and
- stores a separately entered physical measurement beside the visual distance.

The GUI never calls the gripper action, publishes a gripper command, or starts a
hardware backend. Slider movement affects only `/joint_states` and the RViz
model. Its bidirectional calibration ranges intentionally extend beyond the
normal one-direction xacro operating limits. Do not interpret those GUI
ranges as validated physical joint limits.

## Build and launch

```bash
cd /workspaces/ur5_ros2/ur5_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-up-to robotiq_3f_calibration
source install/setup.bash
ros2 launch robotiq_3f_calibration calibration.launch.py
```

The default CSV destination is
`/workspaces/ur5_ros2/gripper_calibration/gripper_samples.csv`. Override it
with `output_file:=/absolute/path/samples.csv` or select another file in the
GUI.

## Suggested fitting workflow

1. Put the real gripper in a settled, unloaded pose using the separately
   supervised controller workflow.
2. Enable `Follow live status`, or enter mode/request/actual register values
   manually.
3. Adjust the model sliders until the visual links match fixed side/front
   photographs or measured real link angles.
4. If a middle link rotates around the wrong location, adjust that finger's
   middle-pivot X/Y/Z offsets. Bend the middle joint away from zero so the
   rotation center is observable; zero angle intentionally preserves the mesh
   pose for every offset. The colored RViz marker is the candidate center. The
   fitting model retains the pre-calibration origin so existing rows with the
   accepted +11.62 mm X offset continue to replay after that correction is
   promoted into the normal articulated xacro.
5. In RViz select the `Publish Point` toolbar tool, then click Point A and
   Point B. The app calculates their Euclidean separation and signed x/y/z
   differences and displays a persistent annotated marker.
6. Enter the independently measured physical separation in `Real measured
   distance`, add photo filenames/notes, and press `Record sample to CSV`.

Pivot values are offsets from the current xacro origins, expressed in each
proximal link's coordinates. They are recorded in both metres and millimetres.
Only the calibration xacro contains the virtual offset/compensation joints;
the normal workcell contains the accepted pivot centers and fixed zero-pose
compensation, but no virtual calibration joints.

## Recalling and duplicating configurations

The `Saved configuration` selector reads the CSV currently shown in `CSV
file`. Press `Refresh saved configurations` after an external edit, then:

- `Load selected` restores the mode/raw values, all eleven joint angles, all
  nine pivot offsets, notes, physical distance, and visual measurement points.
- `Duplicate as new sample` restores the same data but assigns a unique
  `<old_id>_copy` sample ID. Adjust it and press `Record sample to CSV` to save
  a new row.

Loading automatically turns off `Follow live status` so incoming hardware
feedback cannot overwrite the recalled metadata. It moves only the RViz model
and never sends a gripper command.

If a real driver/controller is launched for status and supervised motion, turn
off its mapper to avoid two publishers for the same gripper joints:

```bash
ros2 launch robotiq_3f_controller hardware.launch.py \
  gripper_ip:=<verified_gripper_ip> \
  launch_joint_state_publisher:=false
```

Normal safety rules still apply to that separate launch. The
calibration GUI itself remains visualization-only.

## Measurement limitations

RViz distances are distances in the rendered model, not observations of the
physical gripper. Point picking is limited by the camera view and rendered mesh
surface. Use an orthographic-looking view and repeat important selections from
more than one angle. Physical caliper measurements, a scale in fixed
photographs, or tracked link landmarks remain the calibration ground truth.

The built-in RViz `Measure` tool is also included for quick checks. Its result
is not exported, so use `Publish Point` when the endpoint coordinates and
distance must be stored with a sample.
