# Robotiq FT TCP streamer

This package reads the Robotiq FT300s ASCII stream exposed by the Universal
Robots controller on TCP port 63351. It is intentionally separate from the
serial/USB `robotiq_ft_sensor_hardware` package and from the UR driver's
on-controller wrench broadcaster.

The compatibility output is a `geometry_msgs/msg/WrenchStamped` on
`/robotiq_ft_sensor/wrench`. Unlike the legacy ROS 1 node, samples are labeled
with `ft_measurement_frame`, the measurement frame in the authoritative
workcell description.

Run it independently with:

```bash
ros2 launch robotiq_ft_streamer ft_streamer.launch.py \
  robot_ip:=<robot-ip>
```

Startup zeroing is disabled by default, so output begins immediately with a
zero software offset. The node reconnects after connection failures. If
startup zeroing is explicitly enabled, it restarts an incomplete bias
collection after reconnecting.

Request a new software zero with:

```bash
ros2 service call /robotiq_ft_streamer/zero std_srvs/srv/Trigger '{}'
```

The service waits for the configured sample count and fails on timeout. The
previous offset remains active if the request fails. Zeroing suppresses wrench
publication until the new offset has been computed.

The values are passed through in SI units: force in newtons and torque in
newton-metres. Units under small known loads, axis signs, zeroing, timestamps,
rate, and disconnect/reconnect behavior were validated on the physical
installation on 2026-09-07.
