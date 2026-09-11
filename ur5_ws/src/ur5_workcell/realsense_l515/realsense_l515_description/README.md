# RealSense L515 description

The visual mesh is copied from the installed ROS 2
`realsense2_description` 4.58.1 package, which declares Apache-2.0. That
package ships an L515 mesh but no L515 xacro macro.

The identical mesh in pinned RealSense ROS 4.54.1 has a front-plate origin.
Its `_l515.urdf.xacro` places it in the driver's body frame with translation
`[0.0045, 0, 0.009]` m and roll/yaw both +90 degrees. This component applies
that placement to the visual and transforms the legacy collision box with it.
The box center is therefore `[-0.006456, 0, 0.009]` m in `camera_link`.
The approximate inertia is expressed in the same rotated body geometry axes;
it is not a measured dynamics model.

The collision geometry is a lightweight box matching the bounding dimensions
of the conservative collision mesh used by the legacy workcell. This avoids
using a high-polygon visual mesh for collision checking. The workcell xacro
owns only the mount-to-`camera_link` transform; the RealSense ROS 2 node should
publish its downstream stream and optical frames.

The workcell-level calibrated mount and its provenance are stored in
`ur5_workcell_description/config/camera_extrinsics.yaml`, because the
calibration relates the installed camera to `tool0` rather than describing the
reusable L515 body itself.
