# Robotiq FT300s description

This package contains the FT300 mesh model and mounting plate used by the
legacy workcell, exposed through a ROS 2 xacro macro. It is description-only;
the real workcell's wrench data is expected to arrive through the UR
controller TCP stream, not through a serial hardware plugin.

The assets came from the BSD-3-Clause `robotiq_description` package already
present in this workspace. The exact FT300/FT300s variant and measurement-axis
orientation still require physical verification.
