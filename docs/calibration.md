# Grid calibration

Robots and Cubes stores task geometry in `base_link`. An accepted calibration
defines one fixed, right-handed `base_link -> grid_frame` transform. The
calibration adapter is its sole TF publisher; it publishes only after explicit
acceptance. It never commands the arm, gripper, MoveIt, or a planner.

Mount the calibration pen, manually position it at P0, PX, and PY, and capture
each point. The adapter reads the measured `base_link -> tool0` transform and
calculates the pen-tip point with the complete tool rotation:

`T_base_pen = T_base_tool0 * T_tool0_pen`

The configured pen translation is `[0, 0, 0.315]` m from `tool0`. Therefore a
rotated tool rotates the pen vector; its world direction must never be assumed.
PXY is optional and validates the constructed frame only.

P0/PX/PY validate measured board width, height, angle, and orthogonality.
PXY validates `P0 + width * ex + height * ey`. Tolerances and freshness limits
are in `config/user_settings.yaml`; board dimensions derive from rows, columns,
and cell size rather than a hard-coded 0.54 m.

Calibration is transactional. Starting a draft retains the active result;
canceling or failing validation does the same. Explicit acceptance atomically
writes `runtime_data/calibration.yaml`, then replaces the active transform.
Reload rejects malformed schema, changed board geometry, task frame, or
pen-transform revision and exposes an invalidation reason.

The separate application cube TCP is `cube_grasp_tcp`, `[0, 0, 0.275]` m from
`tool0`. Its configured orientation remains provisional and uncommissioned.
