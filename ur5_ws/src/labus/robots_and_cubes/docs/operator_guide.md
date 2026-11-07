# Calibration and teaching guide

The calibration/teaching workflow below describes the implemented domain logic.
The current package has no runnable calibration ROS node; measured-state
providers and TF publication still need to be wired into a ROS integration.
The mock launch does not start calibration or teaching services.

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

## Application mock (Phase 5)

The application mock is for backend/game development only. Its synthetic
calibration, home, safe, destinations, and enabled cells are clearly marked
`SYNTHETIC_MOCK_*_ONLY`; they are not written to `runtime_data/` and never make
the real UR5 ready. It neither starts nor contacts UR, MoveIt, Robotiq, FT,
camera, dashboard, or controller software. Do not use mock readiness as an
operator authorization for physical setup or robot motion.

If a synthetic execution reports `MAY_HAVE_GRASPED`,
`MAY_HAVE_TRANSPORTED`, or `MAY_HAVE_RELEASED`, inspect the mocked condition
through operator tooling. Confirming that the cube remains at source permits
the existing safe retry path. Confirming it is held/transported or at the
destination ends the round: Phase 5 intentionally supplies no recovery motion.
