# robotiq_3f_driver

C++ Modbus TCP hardware backend for the Robotiq 3-Finger Adaptive Gripper.
It reads eight input registers at address zero and decodes the complete 16-byte
status process image. Commands use Modbus function 0x10 to write eight
registers at address zero.

The process-image mapping was independently ported from Robotiq's
BSD-licensed ROS 1 3F implementation and checked with golden vectors. The TCP
transport and ROS 2 safety/state handling are new C++ implementations; this is
not the official 2F/Hand-E ROS 2 driver with a renamed interface.

Starting the driver connects and polls status. It writes only commands received
from the controller and does not activate or move the gripper on startup.

```bash
ros2 launch robotiq_3f_driver driver.launch.py \
  gripper_ip:=<verified_gripper_ip>
```

The backend topics are internal contracts used by `robotiq_3f_controller`:

- `/robotiq_3f/backend/status`
- `/robotiq_3f/backend/command`

A command received while disconnected or before the first valid status sample
is discarded. Pending commands are cleared after every communication failure
and are never replayed after reconnection. Automatic release is rejected unless
separately enabled.
