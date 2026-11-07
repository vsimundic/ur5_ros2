# Coordinate systems

`base_link` is the authoritative Robots and Cubes task frame. Store every
Cartesian point, calibration marker, grid target, and taught destination with
an explicit `base_link` frame ID. Application code must not silently mix
`world`, `base`, and `base_link`.

The calibration adapter is designed to publish an accepted
`base_link -> grid_frame` transform when wired to a ROS publisher. In
`grid_frame`, increasing columns are `+X`, increasing rows are `+Y`, and
`+Z = +X x +Y` points out of the board. Calibration constructs an orthonormal,
right-handed frame from P0/PX/PY. The optional PXY point checks that frame but
does not change it.

Game handedness is educational 2-D mathematics, not a TF transform. A
left-handed Challenge mapping reflects game coordinates in pure game logic;
it never publishes a left-handed ROS frame.

MoveIt may retain `world` as its internal model frame. A future motion boundary
will explicitly transform application `base_link` targets before planning. This
application does not create MoveIt, motion, or planning interfaces.
