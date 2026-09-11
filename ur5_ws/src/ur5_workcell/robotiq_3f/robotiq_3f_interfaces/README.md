# robotiq_3f_interfaces

Language-neutral ROS 2 interfaces for the complete Robotiq 3-Finger Adaptive
Gripper process image. ROSIDL generates both C++ and Python APIs, so `rclcpp`
drivers and `rclpy` applications use the same messages and action.

The numeric position, speed, force, current, and fault values intentionally
retain the native 0..255 register representation. Physical-unit and articulated
joint mappings must be added only after validation against the installed
gripper.
