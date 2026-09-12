# Calibration and teaching guide

Use the calibration service flow: start a draft, capture P0/PX/PY from fresh
measured state, optionally capture PXY, validate, inspect results, then accept.
Canceling a draft preserves the previous calibration. A stale TF is rejected;
the service never uses a last commanded pose.

Teach `home` and `safe` by manually positioning the robot and capturing the
actual six UR joint names and positions. These are not SRDF named poses. Teach
Cartesian destinations from fresh measured poses in `base_link`: `green_reward`
and either multiple `red_*` slots or a `red_bin`. Each destination may later
use a release pose plus approach and retreat offsets.

Beginner correctness is location-based. The explicit
`teaching.beginner_correct_destination` policy currently maps
`BEGINNER_CORRECT` to `green_reward`; it never infers a destination from cube
colour.

Accepted calibration and teaching data are operator runtime data under
`runtime_data/` and are ignored by Git. The readiness view reports grid,
home, safe, reward, and red-capacity facts. It does not make the robot ready:
cube TCP orientation commissioning, reachability, grasp setup, motion policy,
speeds, Pilz, and physical commissioning remain later gates.
