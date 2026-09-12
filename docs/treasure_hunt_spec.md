# UR5 Coordinate Treasure Hunt
## Complete implementation specification for Codex

> **Phase 6 mode revision:** The piece set and mode behavior in
> [phase_6_game_mode_update.md](phase_6_game_mode_update.md) supersede the
> original red/green mode descriptions below. Existing numeric Standard and
> Challenge interface values are retained; Spatial is the new fifth mode.

# 0. Purpose of this document

Implement an exhibition-ready educational application for a UR5 robot with a Robotiq 3-finger gripper.

The game teaches children coordinate systems by allowing them to select a cube or coordinate on a physical grid and then watching the robot execute their choice.

The implementation uses:

- ROS 2 Jazzy;
- Docker;
- UR5;
- Robotiq 3-finger gripper;
- MoveIt 2;
- Pilz Industrial Motion Planner as the primary motion strategy;
- RRT* as a fallback where appropriate;
- a child-facing graphical application;
- a separate operator interface;
- a physical 6×6 board;
- manually placed cubes and coordinate-origin object in V1.

The system must prioritize:

1. safety;
2. repeatability;
3. predictable robot motion;
4. robustness during an exhibition;
5. simple operator workflow;
6. attractive and understandable gameplay for children.

---

# 1. Instructions to the implementation agent

Before writing integration code:

1. Inspect the existing repository/workspace.
2. Identify all existing ROS packages.
3. Identify whether the physical robot configuration is UR5 or UR5e.
4. Identify the actual:
   - robot base frame;
   - MoveIt planning frame;
   - MoveIt planning group;
   - end-effector link;
   - configured TCP;
   - robot controller;
   - Robotiq command interface;
   - Robotiq feedback interface;
   - configured MoveIt planning pipelines;
   - actual RRT* planner ID;
   - Docker startup workflow;
   - existing UR calibration configuration.
5. Preserve currently working robot infrastructure.
6. Adapt the game around the existing drivers instead of replacing working drivers.
7. Do not invent ROS topic, action, service, group, joint or frame names.
8. Discover them from the project.
9. No robot motion may occur automatically at application startup.
10. The application must support mock execution without hardware.
11. The application must support plan-only commissioning.
12. All values intended to be adjusted by the user must be configurable.
13. Do not hide important physical parameters as source-code constants.

If something required for hardware integration cannot be discovered, clearly document it rather than guessing.

---

# 2. Language requirement

## 2.1 Child-facing application

**The entire child-facing UI must be in Croatian.**

No English engineering or game text should appear in Kid Mode.

This includes:

- buttons;
- instructions;
- success messages;
- failure messages;
- waiting messages;
- coordinate questions;
- attempt indicators;
- error/recovery placeholders shown to children;
- difficulty names if ever exposed to children.

Coordinate notation remains mathematical:

```text
(-2, +1)
(+3, -1)
```

but all surrounding language must be Croatian.

Examples:

```text
ROBOTSKA POTRAGA ZA BLAGOM
```

```text
Pronađi zelenu kocku s blagom!
```

```text
Koja se kocka nalazi na koordinatama (-2, +1)?
```

```text
Na kojim se koordinatama nalazi blago?
```

```text
Robot provjerava tvoj odgovor...
```

```text
Bravo!
Blago je pronađeno!
```

```text
Još jedan pokušaj!
```

```text
Dobar pokušaj!

Blago se nalazilo na koordinatama:

(-2, +1)
```

If the robot has a recoverable hardware problem, Kid Mode should not expose engineering language.

Use something neutral such as:

```text
Robot trenutačno treba malu pomoć.
```

The operator sees the real diagnostic message.

---

# 3. Croatian text storage

Do not scatter Croatian strings throughout React/components/source files.

Store child-facing text centrally.

Recommended:

```text
config/
    user_settings.yaml
    child_text_hr.yaml
```

or equivalent structured files.

For example:

```yaml
title: "ROBOTSKA POTRAGA ZA BLAGOM"

common:
  next: "Dalje"
  start: "Pokreni igru"
  new_game: "Nova igra"

easy:
  instruction: "Pronađi zelenu kocku s blagom!"

beginner:
  instruction: "Koja se kocka nalazi na ovim koordinatama?"

standard:
  instruction: "Na kojim se koordinatama nalazi blago?"

motion:
  waiting: "Robot provjerava tvoj odgovor..."

attempts:
  one_left: "Još jedan pokušaj!"

success:
  title: "Bravo!"
  text: "Blago je pronađeno!"

failure:
  title: "Dobar pokušaj!"
  answer_prefix: "Blago se nalazilo na koordinatama:"
```

This allows copy changes without rebuilding game logic.

UTF-8 must be used correctly.

Croatian characters such as:

```text
č ć ž š đ
```

must display correctly.

---

# 4. Operator interface language

The operator UI does not have to obey the Croatian-only restriction.

It may initially be English.

Its architecture should make later localization possible.

Do not mix child-facing and operator-facing text resources.

---

# 5. User-editable configuration philosophy

Create a main configuration file intended for normal user/operator editing:

```text
config/user_settings.yaml
```

The purpose is:

> If a parameter is reasonably safe and understandable to change without editing source code, put it here.

Examples include:

- board dimensions;
- square size;
- cube size;
- number of red cubes;
- number of attempts;
- enabled game modes;
- allowed origin positions;
- challenge rotations;
- challenge handedness;
- adjacency rules;
- generation-quality rules;
- animation timing;
- transit clearance;
- pre-grasp clearance;
- UI behavior;
- reward/drop strategy;
- mock-mode timing;
- calibration tolerances.

Do not put low-level dangerous commissioning values in this main file if they should not be casually edited.

---

# 6. Configuration tiers

Use three levels.

## Level 1 — normal user configuration

```text
config/user_settings.yaml
```

Safe/common values.

## Level 2 — advanced robot commissioning

```text
config/robot_commissioning.yaml
```

Contains values such as:

- authoritative application and MoveIt frame identifiers;
- the application cube-pinch TCP relative to `tool0`;
- the calibration pen-tip translation relative to `tool0`;
- allowed game joint ranges;
- cell-specific grasp-yaw overrides;
- trajectory excursion limits;
- MoveIt tolerances;
- planner configuration;
- advanced velocity/acceleration settings.

This should be clearly marked:

```text
ADVANCED — change only during robot commissioning.
```

## Level 3 — runtime generated data

```text
runtime_data/
    calibration.yaml
    taught_poses.yaml
```

These files are generated by the application.

The user should normally modify them using the operator UI, not manually.

---

# 7. Configuration loading

At startup:

1. load defaults;
2. load `user_settings.yaml`;
3. validate it against a schema;
4. load advanced commissioning configuration;
5. load runtime calibration;
6. load taught positions.

If invalid configuration exists:

- do not silently substitute nonsense values;
- clearly tell the operator which property is invalid;
- refuse real robot execution if necessary.

Prefer typed configuration models, for example Pydantic on the Python side.

---

# 8. Example user configuration

Create a clean default file approximately like:

```yaml
application:
  name: "UR5 Coordinate Treasure Hunt"

  child_language: "hr"

game:
  enabled_modes:
    - easy
    - beginner
    - standard
    - challenge

  attempts: 2

  cubes:
    red_count: 4
    green_count: 1

  standard:
    central_origin_margin_cells: 1

  challenge:
    rotations_deg:
      - 0
      - 90
      - 180
      - 270

    enable_left_handed: true

board:
  rows: 6
  columns: 6

  cell_size_m: 0.09

cube:
  size_m:
    x: 0.06
    y: 0.06
    z: 0.06

generation:
  allow_adjacent_cubes: true
  minimum_cell_distance: 1

  favor_coordinate_sign_variety: true

  require_positive_x: false
  require_negative_x: false
  require_positive_y: false
  require_negative_y: false

motion:
  grid_transit_clearance_m: 0.10
  pregrasp_clearance_m: 0.10

  default_grasp_yaw_deg: 0

calibration:
  maximum_side_length_error_m: 0.005
  maximum_angle_error_deg: 1.0

ui:
  show_attempt_hearts: true
  success_screen_seconds: 5
  failure_screen_seconds: 6

  sound_enabled: true

mock:
  movement_duration_seconds: 2.0
```

Values must be validated.

Do not assume every conceivable value is valid.

---

# 9. Configurable cube count

Default:

```text
4 red cubes
1 green cube
5 cubes total
```

However:

```text
red_count
```

must be configurable through `user_settings.yaml`.

Exactly one green treasure cube is required for Standard and Challenge modes.

Therefore:

```text
total_cubes = red_count + 1
```

The number of Standard/Challenge coordinate answers automatically equals:

```text
total_cubes
```

Do not hardcode exactly five answer buttons into the UI.

The default remains five because that is the intended exhibition setup.

Reasonable configuration validation should prevent obviously unusable values.

For example:

```text
red_count >= 1
total cubes < available board cells
```

The UI should also reject configurations producing an unreasonable number of touchscreen answers.

Set a sensible supported upper bound, documented in configuration validation.

---

# 10. Physical changes require recommissioning

Some properties are editable but correspond to real physical geometry.

Examples:

```text
cube.size
board.cell_size
board.rows
board.columns
```

Changing these is allowed in configuration, but the operator UI should warn:

```text
Promjena ove postavke zahtijeva ponovnu provjeru fizičkog sustava.
```

These changes may require:

- recalibration;
- grasp-height adjustment;
- collision-scene changes;
- adjacency testing;
- recommissioning grid cells.

Do not pretend changing physical geometry is merely cosmetic.

---

# 11. Physical board

Default board:

```text
6 columns
6 rows
90 mm square size
```

Total active area:

```text
540 × 540 mm
```

All game objects occupy cell centers.

Not intersections.

This guarantees integer child coordinates.

Internal indexing:

```text
column = 0 ... columns-1
row    = 0 ... rows-1
```

Default cell center:

```text
x = (column + 0.5) * cell_size
y = (row    + 0.5) * cell_size
```

relative to `grid_frame`.

---

# 12. Cube geometry

Default:

```text
60 × 60 × 60 mm
```

Configurable.

Board surface:

```text
grid z = 0
```

Default cube center:

```text
z = cube_height / 2
```

Default cube top:

```text
z = cube_height
```

Do not hardcode `0.03` or `0.06` into motion code.

---

# 13. Origin object

The origin-frame object occupies exactly one grid cell center.

No cube may occupy that cell.

Support logical origin types:

```text
RIGHT_HANDED
LEFT_HANDED
```

Left-handed rounds can be disabled through configuration.

---

# 14. ROS coordinate frames

All ROS TF frames must remain valid right-handed frames.

All application task geometry and Cartesian targets are authored and stored in
`base_link`. Every stored Cartesian pose must carry its frame identifier. Do
not mix `world`, `base`, and `base_link` implicitly. MoveIt may retain `world`
as its internal model/planning frame; the motion layer must explicitly
transform each `base_link` target when MoveIt requires another frame.

Expected hierarchy:

```text
base_link
    |
    +-- grid_frame
            |
            +-- game_origin_frame
```

`grid_frame`:

- physical calibrated board frame.

`game_origin_frame`:

- translation to current origin cell;
- legal rotational orientation;
- always valid right-handed TF.

Do not create a mirrored TF.

---

# 15. Grid convention

Internally:

```text
+grid_x = increasing column
+grid_y = increasing row
+grid_z = out of playing surface
```

Calibration point ordering must produce:

```text
grid_x × grid_y = grid_z
```

with `grid_z` pointing away from the board.

---

# 16. Educational game coordinate convention

A game coordinate system consists of:

```text
origin_cell
rotation
handedness
```

Rotation defaults to:

```text
0°
90°
180°
270°
```

Use exact integer matrices.

Do not use floating point sine/cosine for 90° game transformations.

Conceptually:

```text
delta_grid = A * game_coordinate
```

where:

```text
A = R(rotation) * H(handedness)
```

Right-handed:

```text
H = [[1,0],
     [0,1]]
```

Left-handed educational mapping:

```text
H = [[1, 0],
     [0,-1]]
```

For a cube:

```text
delta_grid =
[
 cube.column - origin.column,
 cube.row    - origin.row
]
```

Then:

```text
game_coordinate = transpose(A) * delta_grid
```

All game coordinates must remain integers.

---

# 17. Left-handed challenge

The left-handed system is an educational/game convention.

Do not represent it as a left-handed ROS TF transform.

Its mapping exists in the game logic.

If handedness is taught as a 3-D concept, the printed origin piece should clearly show:

```text
X
Y
Z
```

with Z visible.

---

# 18. Calibration system

The operator has a removable pen.

The pen is mounted repeatably to the robot.

Its tip position relative to `tool0` is known:

```text
tool0 -> pen_tip = [0.0, 0.0, 0.315] m
```

Store the parent frame and translation in advanced application configuration.
Pen-tip orientation is not required for three-point board calibration. For P0,
PX, and PY, compose the measured `tool0` pose in `base_link` with this
translation and store the resulting pen-tip point in `base_link`.

Do not use the cube-pinch TCP to capture board calibration points.

---

# 19. Calibration points

Use three permanent border markers:

```text
PY ●──────────────────────●
   │                      │
   │       PLAY AREA      │
   │                      │
P0 ●──────────────────────● PX
```

For the default board:

```text
P0 -> PX = 0.54 m
P0 -> PY = 0.54 m
```

If board dimensions change, calculate expected lengths from:

```text
columns * cell_size
rows * cell_size
```

Do not hardcode 0.54 m into calibration logic.

---

# 20. Calibration workflow

Operator:

```text
Options
 -> Calibration
 -> Calibrate Grid
```

UI instructs:

```text
Mount calibration pen.
```

Then:

```text
Step 1/3
Move the pen tip to P0.

[Save P0]
```

```text
Step 2/3
Move the pen tip to PX.

[Save PX]
```

```text
Step 3/3
Move the pen tip to PY.

[Save PY]
```

When saving:

- obtain actual current robot state;
- calculate pen-tip position in `base_link`;
- do not save the flange position;
- do not assume the normal TCP equals pen tip.

---

# 21. Calibration mathematics

Given:

```text
P0
PX
PY
```

calculate:

```text
ex = normalize(PX - P0)

temp_y = PY - P0

ez = normalize(ex × temp_y)

ey = ez × ex
```

Construct:

```text
base_link -> grid_frame
```

with:

```text
translation = P0
rotation axes = [ex ey ez]
```

The resulting axes must be orthonormal.

---

# 22. Calibration validation

Show:

```text
measured X length
measured Y length
XY angle
orthogonality error
```

Expected X/Y lengths come from board configuration.

Configurable tolerances:

```text
maximum_side_length_error_m
maximum_angle_error_deg
```

If invalid:

- do not save calibration as valid;
- explain the failed check;
- allow recalibration.

---

# 23. Optional fourth point

Support optional `PXY`.

Predicted:

```text
PXY_expected =
P0
+ board_width  * ex
+ board_height * ey
```

Operator may manually capture physical PXY.

Display Euclidean prediction error.

This validates calibration but does not construct the frame.

---

# 24. Calibration persistence

Save accepted calibration to:

```text
runtime_data/calibration.yaml
```

Include:

```text
schema_version
timestamp
P0
PX
PY
grid transform
quality metrics
optional fourth-point error
```

On startup:

- load last valid calibration;
- display timestamp;
- allow recalibration;
- allow invalidation.

Missing/invalid calibration prevents real game execution.

---

# 25. UR factory calibration

Use the robot-specific UR kinematic calibration already associated with the physical robot.

Do not silently substitute generic nominal UR geometry.

During initial repository inspection verify this.

---

# 26. Game modes

Implement four modes:

```text
Easy
Beginner
Standard
Challenge
```

Internally these may have English enum names.

Child-facing mode names, if displayed, must be Croatian.

Recommended:

```text
Lako
Početnik
Standardno
Izazov
```

Difficulty selection may initially remain operator-only.

---

# 27. Easy mode

For the youngest children.

No coordinate reasoning.

Croatian instruction:

```text
Pronađi zelenu kocku s blagom!
```

Child sees the visual board.

Child taps a cube.

If red:

- no robot movement;
- no attempt consumed;
- show a friendly hint.

For example:

```text
Pokušaj ponovno. Potraži zelenu kocku sa zvjezdicom!
```

If green:

1. lock input;
2. robot picks green cube;
3. robot delivers it to green reward destination;
4. display success.

---

# 28. Beginner mode

Educational goal:

> Given a coordinate, select the cube located there.

Default origin configuration:

```text
right handed
rotation 0°
```

Child sees:

```text
Koja se kocka nalazi na koordinatama

(-2, +1)?
```

Child taps a cube.

Correctness depends on coordinate location, not cube color.

Use configured number of attempts.

On a wrong physical cube:

1. robot picks it;
2. moves it to red/general drop destination;
3. mark it unavailable;
4. decrement logical attempt.

On correct answer:

- robot picks the selected correct cube;
- display Croatian success.

Beginner correctness is location-based. `BEGINNER_CORRECT` must map through an
explicit configured logical destination (`green_reward` or `beginner_demo`);
do not derive that destination from the cube colour.

---

# 29. Standard mode

Main game.

Defaults:

```text
RIGHT handed
rotation = 0°
```

The green cube is the treasure.

Child sees all actual cube coordinates as answer choices.

Exactly one coordinate corresponds to the green cube.

All others correspond to red cubes.

Croatian question:

```text
Na kojim se koordinatama nalazi blago?
```

---

# 30. Standard origin restrictions

For the default 6×6 grid, origins are restricted to the central 4×4 cells:

```text
columns 1..4
rows    1..4
```

Do not hardcode those indices.

Derive allowed cells from:

```text
central_origin_margin_cells: 1
```

Meaning:

```text
origin column >= margin
origin column < columns - margin

origin row >= margin
origin row < rows - margin
```

Default margin:

```text
1
```

This automatically produces central 4×4 on a 6×6 board.

---

# 31. Standard correct answer

If green coordinate selected:

1. lock UI;
2. plan;
3. execute pickup;
4. deliver green cube;
5. display:

```text
Bravo!

Blago je pronađeno!
```

Then reinforce:

```text
Koordinate blaga:

X = -2
Y = +1
```

---

# 32. Standard wrong answer

For first wrong answer:

1. selected coordinate identifies a red cube;
2. robot removes that red cube;
3. place it at red destination;
4. mark answer disabled;
5. decrement attempts.

For default two attempts:

```text
Još jedan pokušaj!
```

After final wrong answer:

```text
Dobar pokušaj!

Blago se nalazilo na koordinatama:

(-2, +1)
```

---

# 33. Challenge mode

Challenge mode extends Standard.

Allow:

```text
0°
90°
180°
270°
```

and optionally:

```text
RIGHT
LEFT
```

all controlled through `user_settings.yaml`.

Operator setup must display:

- origin cell;
- origin physical rotation;
- handedness/piece type;
- cube positions.

Child sees the correct visual representation of the origin axes.

Never use child-facing language such as:

```text
robot coordinates
robot frame
```

Use Croatian educational language such as:

```text
koordinatni sustav
ishodište
X-os
Y-os
koordinate
```

---

# 34. Cube generation

Each round contains:

```text
red_count configured red cubes
1 green cube
1 origin object
```

Default:

```text
4 red
1 green
```

Rules:

- unique cells;
- cube never overlaps origin;
- green count exactly 1;
- all chosen cells robot-enabled;
- all coordinates unique automatically because cell positions are unique.

---

# 35. Round data model

Generate and store:

```text
round_id
random_seed
mode
origin_cell
rotation
handedness

cubes:
  id
  color/type
  cell
  game_coordinate

green_cube_id

beginner_target_cube_id if applicable

answer_order
attempts_remaining
selected_answers
removed_cubes
round_state
```

Generate once.

Frontend must never independently regenerate game information.

---

# 36. Random seed

Support optional explicit random seed.

Useful for:

- debugging;
- reproducing exhibition failures;
- automated tests.

Log every generated round's seed.

---

# 37. Generation quality

Configurable:

```text
allow_adjacent_cubes
minimum_cell_distance
favor_coordinate_sign_variety

require_positive_x
require_negative_x
require_positive_y
require_negative_y
```

Default Standard should favor rounds that contain useful positive and negative values.

Do not make impossible constraints silently loop forever.

Use a bounded generation-attempt count.

If generation fails:

```text
Could not generate a valid layout with current settings.
```

show operator-side diagnostics.

---

# 38. Adjacent-cube clearance

Default physical geometry:

```text
cell pitch = 90 mm
cube width = 60 mm
```

Therefore adjacent cubes leave:

```text
30 mm
```

between faces.

Physically test whether the Robotiq 3-finger gripper can safely operate when neighboring cubes are present.

If not:

```yaml
generation:
  allow_adjacent_cubes: false
```

or apply stricter separation rules.

Do not solve this by guessing.

---

# 39. Accessibility

Correctness cannot rely only on:

```text
red
green
```

Green treasure should also display:

```text
star / treasure symbol
```

Red cubes should use a different symbol.

Kid UI should remain understandable with red-green color vision deficiency.

---

# 40. Operator setup flow

Normal round:

```text
Generate Round
     |
     v
Operator sees board layout
     |
     v
Operator manually places:
- origin
- cubes
     |
     v
[Pieces placed correctly]
     |
     v
Round preflight
     |
     v
Kid interface unlocked
```

Manual setup is V1.

Do not implement automatic cube setup initially.

---

# 41. Setup board visualization

Operator preview must clearly show:

- grid;
- origin;
- X and Y arrows;
- handedness;
- green cube;
- red cubes;
- cell placement.

For Challenge, orientation must be unambiguous.

---

# 42. Motion architecture

Primary:

```text
Pilz Industrial Motion Planner
```

Use:

```text
PTP
LIN
```

Fallback:

```text
OMPL RRT*
```

using the actual configured planner ID discovered from MoveIt configuration.

Do not assume a planner string from this document.

---

# 43. Motion philosophy

The robot should appear predictable and repeatable.

Do not ask a sampling planner to discover arbitrary complete pick trajectories when known structured motion is possible.

Desired family:

```text
safe/transit pose
      |
      | PTP
      v
pre-grasp
      |
      | LIN down
      v
grasp
      |
      | LIN up
      v
pre-grasp
      |
      | PTP
      v
destination approach
      |
      | LIN down
      v
release
      |
      | LIN up
      v
retreat
```

---

# 44. Grid transit height

Configurable in `user_settings.yaml`.

Default:

```text
grid_transit_clearance_m: 0.10
```

The intended commissioning range is roughly:

```text
0.05–0.10 m
```

but actual value must be physically tested.

Define clearance relative to the tallest board object as appropriate.

---

# 45. Pre-grasp height

Configurable:

```text
pregrasp_clearance_m
```

Do not hardcode.

---

# 46. Grasp orientation

The application cube-pinch TCP is `cube_grasp_tcp`, relative to `tool0`:

```text
translation = [0.0, 0.0, 0.275] m
```

Its X and Y offsets are zero so it lies on the tool center axis. Preserve the
currently reviewed tooling orientation in application configuration until a
separate orientation is physically commissioned; it is provisional and does
not make real motion ready. Do not modify the reusable
workcell's tactile/reference `grasp_tcp` for this application setting.

Default:

```text
top-down
pinch grasp
gripper yaw = configured default
```

The educational origin orientation does not determine gripper orientation.

These are independent.

Default grasp yaw should preferably stay constant.

---

# 47. Outermost cells

Some outside cells may require approximately 45° wrist/gripper yaw.

Support cell-specific overrides in advanced commissioning config:

```yaml
grasp_orientation:
  default_yaw_deg: 0

  cell_overrides:
    "0,0": 45
    "5,0": -45
```

Do not add overrides until physical commissioning demonstrates they are required.

---

# 48. Commissioned-cell database

Maintain:

```text
config/cell_commissioning.yaml
```

Example:

```yaml
cells:
  "0,0":
    reachable: true
    grasp_yaw_deg: 45

  "1,0":
    reachable: true
    grasp_yaw_deg: 0

  "5,5":
    reachable: false
```

Round generation must never select:

```text
reachable: false
```

This allows individual cells to be disabled without changing code.

---

# 49. Joint constraints

Low-level game joint ranges belong in:

```text
robot_commissioning.yaml
```

not in casual `user_settings.yaml`.

Purpose:

- consistent shoulder posture;
- consistent elbow posture;
- prevent wrist wind-up;
- prevent strange IK solutions;
- prevent unnecessary large rotations.

Do not invent values.

Commission them physically.

---

# 50. Orientation constraints

During board operation:

- tool remains near intended downward orientation;
- yaw variation is allowed only where needed;
- tolerances configurable in advanced commissioning file.

Avoid constraints so strict that valid outer cells become impossible.

---

# 51. Trajectory policy

Before execution validate every trajectory.

Check:

- planning succeeded;
- trajectory non-empty;
- joint points inside approved game ranges;
- no unexpected wraparound;
- per-joint excursion below configured limit;
- orientation constraints respected;
- collision-free;
- start state near real current state;
- no unexpected descent into board plane.

Failure:

```text
DO NOT EXECUTE
```

Return recoverable motion error.

---

# 52. RRT* fallback

RRT* is only fallback for suitable free-space motion.

Do not replace controlled vertical pick/drop `LIN` segments with arbitrary RRT* paths.

Fallback plans must pass the same motion-policy validation.

---

# 53. Motion speed

Use configurable values.

Simple/common speed scaling may live in `user_settings.yaml` if bounded safely.

More advanced motion limits belong in commissioning config.

Support at least:

```text
PTP transit speed
LIN approach speed
LIN lift speed
LIN release speed
```

Never automatically command maximum speed.

---

# 54. Planning scene

Include:

- board;
- table/support;
- origin object;
- all cubes;
- destination areas;
- fixed obstacles.

Cubes can initially use box collision geometry.

When a cube is grasped:

1. remove/attach appropriately;
2. attach to end effector;
3. transport;
4. detach at destination;
5. update scene.

Removed red cubes must disappear from their old grid locations.

---

# 55. Round preflight

Before child interaction verify every selectable cube.

At minimum:

- configured cell enabled;
- valid grasp pose;
- valid IK;
- no obvious joint-policy violation.

Preferably also perform planning feasibility checks.

If invalid:

```text
Round cannot be executed safely.
Generate another layout.
```

Do not allow the child to encounter a known impossible cube.

---

# 56. Taught positions

Provide operator UI for teaching:

```text
home
safe pose
green reward destination
red destination(s)
```

Home and safe positions should preferably be stored as joint values.

Destination may store:

```text
approach pose
release pose
retreat pose
```

or:

```text
release pose + configured offsets
```

---

# 57. Red drop destination

Because more than one red cube can be removed, do not assume one exact drop pose can hold every cube.

Support:

### Multiple slots

```text
red_slot_1
red_slot_2
red_slot_3
...
```

or:

### Bin/tray

A physical container accepting multiple cubes.

Number of required red slots should be compatible with configured attempts.

---

# 58. Green destination

Green cube goes to a reward location/tray outside the robot's active workspace.

Robot:

1. places cube;
2. releases cube;
3. retreats;
4. only then UI may encourage taking reward.

---

# 59. Gripper abstraction

Create an application-level gripper adapter.

Logical operations:

```text
initialize
open
close_for_cube
stop
get_status
```

Optional:

```text
object_detected
```

Only expose object detection if the actual driver/hardware interface supports it reliably.

---

# 60. Hardware failures

These are **not incorrect answers**:

```text
planning failure
trajectory validation failure
execution failure
protective stop
robot disconnected
gripper failure
controller error
object detection failure
```

Child attempt remains unchanged.

Enter:

```text
ROBOT_ERROR
```

---

# 61. Game state machine

Use an explicit state machine.

Recommended:

```text
STARTUP
IDLE
ROUND_GENERATED
WAITING_FOR_PHYSICAL_SETUP
ROUND_PREFLIGHT
WAITING_FOR_CHILD
EXECUTING_SELECTION
SUCCESS
FAILED
ROBOT_ERROR
ABORTING
CALIBRATION
TEACHING_POSITION
```

---

# 62. Standard flow

```text
IDLE
 |
 | Generate
 v
ROUND_GENERATED
 |
 v
WAITING_FOR_PHYSICAL_SETUP
 |
 | Operator confirms
 v
ROUND_PREFLIGHT
 |
 | valid
 v
WAITING_FOR_CHILD
 |
 | selection
 v
EXECUTING_SELECTION
 |
 +---- correct ----------------> SUCCESS
 |
 +---- wrong + attempts -------> WAITING_FOR_CHILD
 |
 +---- final wrong ------------> FAILED
 |
 +---- hardware problem -------> ROBOT_ERROR
```

---

# 63. Robot error recovery

Do not restart the whole application for routine errors.

Operator should see:

```text
Robot operation failed

Reason:
PLANNING_FAILED

Round:
42

Attempt:
1 / 2

Selected:
(+2,-1)

[Retry Motion]

[Move to Safe Pose]

[Abort Round]

[Return Home]
```

Preserve round data.

Preserve attempts.

---

# 64. Safety faults

Do not automatically defeat or clear robot safety systems.

Application may:

- detect safety state;
- show it to operator;
- wait for recovery;
- reconnect when appropriate.

Deliberate operator action remains required where the robot safety workflow requires it.

---

# 65. Home application control

Provide a persistent application recovery/home action.

Meaning:

```text
Abort current game
Return software to idle/home
```

This is not an emergency stop.

Never label it as such.

---

# 66. UI architecture

Implement two logical interfaces:

```text
Kid UI
Operator UI
```

Recommended web routes:

```text
/kid
/operator
```

These may run on:

- same computer;
- separate browser windows;
- separate displays;
- tablet + main monitor.

---

# 67. Preferred frontend technology

Preferred:

```text
TypeScript
React
Vite
```

with browser-based UI.

Advantages needed here:

- touchscreen interaction;
- animation;
- fullscreen kiosk mode;
- responsive layout;
- easy Croatian typography/text;
- sound effects.

A Python Qt/QML frontend is acceptable if the existing project makes it materially simpler, but preserve two-interface architecture.

---

# 68. UI gateway

Browser must not directly expose raw robot controls.

Recommended chain:

```text
Kid / Operator browser
         |
         v
UI gateway
         |
         v
ROS application nodes
```

Use WebSockets for live state.

Gateway may use FastAPI or equivalent.

---

# 69. Kid UI design

Kid UI must feel like a game.

Use:

- large controls;
- large coordinate text;
- clear symbols;
- minimal text;
- friendly animation;
- attempt indicators;
- no engineering terminology.

Possible title:

```text
ROBOTSKA POTRAGA ZA BLAGOM
```

---

# 70. Input lockout

As soon as child makes a valid selection:

- disable all answer input;
- prevent double-click;
- send exactly one logical selection;
- show:

```text
Robot provjerava tvoj odgovor...
```

Do not enable input until result/recovery is resolved.

---

# 71. Attempt indicator

If enabled by configuration:

Default two attempts:

```text
♥ ♥
```

After first wrong answer:

```text
♥ ♡
```

with:

```text
Još jedan pokušaj!
```

Generalize this to configured attempt count.

Do not hardcode two hearts.

---

# 72. Operator UI

Operator interface includes:

- robot status;
- MoveIt status;
- gripper status;
- calibration status;
- generated round;
- physical setup preview;
- mode selection;
- Generate;
- Confirm Pieces;
- Abort;
- Recovery;
- Calibration;
- Teach positions;
- diagnostics;
- advanced readiness.

---

# 73. Readiness screen

Before real game:

```text
Robot
MoveIt
Gripper
Grid calibration
Home pose
Safe pose
Green destination
Red destination
Planning scene
```

all need readiness indicators.

Example:

```text
Robot              ✓
MoveIt             ✓
Gripper             ✓
Grid calibration    ✓
Reward destination  ✓
Red drop            ✓

READY TO PLAY
```

Operator language may remain English.

---

# 74. Application backend packages

Recommended:

```text
treasure_hunt_interfaces/

treasure_hunt_game/

treasure_hunt_calibration/

treasure_hunt_motion/

treasure_hunt_ui_gateway/

treasure_hunt_web/

treasure_hunt_bringup/
```

Adapt names if repository already has conventions.

---

# 75. Responsibility boundaries

## Game manager

Owns:

- state;
- round;
- attempts;
- correctness;
- difficulty;
- cube identity.

Does not know:

- driver topic names;
- detailed MoveIt implementation.

## Calibration manager

Owns:

- captured points;
- board transform;
- validation;
- persistence.

## Motion executor

Owns:

- MoveIt;
- Pilz;
- RRT* fallback;
- planning scene;
- gripper adapter;
- trajectory validation.

Does not decide:

```text
correct/wrong
```

## UI gateway

Owns frontend communication.

It is not game authority.

---

# 76. Motion operation ROS Action

Use a ROS Action for long robot tasks.

Conceptually:

```text
ExecutePickPlace
```

Feedback:

```text
PLANNING
MOVING_TO_PREGRASP
DESCENDING
GRASPING
LIFTING
MOVING_TO_DESTINATION
RELEASING
RETREATING
```

Result:

```text
SUCCESS
```

or structured failure:

```text
error_code
error_message
```

---

# 77. Calibration API

Logical operations:

```text
StartCalibration
CaptureP0
CapturePX
CapturePY
Validate
Accept
Cancel
```

Exact ROS interface grouping may be optimized.

---

# 78. Teach-position API

Logical operations:

```text
CaptureHome
CaptureSafe
CaptureDestination
DeleteDestination
ListTaughtPositions
```

Capture actual robot state.

Not last commanded state.

---

# 79. Game state publication

Publish a complete current state snapshot.

Newly connected UI must immediately obtain latest state.

Use appropriate ROS QoS or explicit state-fetch endpoint.

Browser refresh must not reset the current game.

---

# 80. Logging

Persist structured event information.

At minimum:

```text
timestamp
round_id
seed
mode
origin
rotation
handedness
cube positions
child selections
attempt result
planner used
motion result
robot error
operator abort
calibration event
```

JSONL is sufficient.

Database not necessary.

---

# 81. Mock mode

Provide:

```text
mock_execution: true
```

In mock mode:

- no hardware commands;
- state machine fully active;
- mock action feedback;
- simulated success/failure;
- full UI works.

Mock motion timing should come from `user_settings.yaml`.

---

# 82. Plan-only mode

Provide:

```text
plan_only: true
```

Plans and validates robot motion.

Does not execute.

May use RViz for engineering verification.

RViz is never the Kid UI.

---

# 83. Startup behavior

Startup must:

1. load config;
2. load runtime calibration;
3. load taught poses;
4. connect ROS interfaces;
5. initialize state;
6. display readiness.

It must not move robot.

---

# 84. Safety

Physical safety remains outside this application and includes:

- workspace separation;
- UR safety settings;
- E-stop;
- operator supervision.

Application rules:

- no motion at startup;
- no motion with invalid calibration;
- no execution of invalid trajectory;
- no child manual robot controls;
- no automatic safety defeat/reset;
- reward delivered outside active robot workspace.

---

# 85. Tests — configuration

Add automated tests for configuration.

Verify:

- default file loads;
- invalid negative cube count rejected;
- impossible grid rejected;
- zero cell size rejected;
- cube larger than obviously invalid geometric bounds warned/rejected as appropriate;
- attempts >= 1;
- one green cube enforced;
- unsupported challenge angles rejected;
- origin margins valid;
- user config does not override forbidden low-level fields.

---

# 86. Tests — coordinate system

Exhaustively test:

- all cells;
- all legal origins;
- 4 rotations;
- right handed;
- left handed;
- mapping grid→game;
- mapping game→grid;
- round trip;
- integer output.

---

# 87. Tests — round generator

Generate thousands of rounds.

Assert:

- correct configured cube count;
- correct red count;
- one green;
- no duplicate cells;
- no origin overlap;
- valid Standard origin region;
- valid Challenge settings;
- all answer coordinates correspond to actual cubes;
- correct green coordinate identified.

---

# 88. Tests — Croatian UI

Add tests ensuring Kid UI has no accidental English fallback for required screens.

At minimum verify Croatian content for:

- home;
- Easy;
- Beginner;
- Standard;
- Challenge;
- waiting;
- success;
- first wrong answer;
- final failure;
- robot-error placeholder.

If translation key missing in Kid Mode:

- treat it as an error during development;
- do not silently display English fallback.

---

# 89. Tests — calibration

Synthetic tests:

- exact board;
- translated board;
- rotated board;
- measurement noise;
- bad side length;
- incorrect angle;
- optional fourth point.

Check orthonormal transform.

---

# 90. Tests — state machine

Test:

### Correct first attempt

```text
WAITING
 -> EXECUTING
 -> SUCCESS
```

### Wrong then correct

```text
WAITING
 -> EXECUTING
 -> WAITING
 -> EXECUTING
 -> SUCCESS
```

### All attempts wrong

```text
WAITING
 -> EXECUTING
 -> ...
 -> FAILED
```

Must work for configurable attempt count, not only two.

### Robot failure

```text
WAITING
 -> EXECUTING
 -> ROBOT_ERROR
 -> RETRY
 -> EXECUTING
```

Attempt count unchanged.

### Abort

Test from all meaningful states.

---

# 91. Frontend tests

Test:

- Croatian Kid UI;
- dynamic cube/answer count;
- attempts rendered dynamically;
- button lockout;
- reconnect behavior;
- setup screen;
- mode behavior;
- success;
- failure;
- operator recovery;
- calibration wizard;
- teach-position wizard.

---

# 92. Commissioning workflow

After software implementation:

1. verify UR factory calibration;
2. calibrate grid;
3. teach home;
4. teach safe pose;
5. teach green destination;
6. teach red destination(s);
7. validate every grid cell;
8. determine grasp Z;
9. determine gripper opening/closing values;
10. determine required edge-cell yaw;
11. determine joint ranges;
12. tune trajectory policy;
13. tune transit clearance;
14. tune speeds;
15. test adjacent-cube clearance;
16. test all game modes;
17. test hardware recovery.

---

# 93. Acceptance criteria

MVP is complete when the following work.

## Configuration

Operator can change normal values such as:

```text
red cube count
attempts
cube dimensions
board dimensions
origin margin
enabled challenge orientations
left-handed mode
grid transit clearance
generation rules
UI timing
```

by editing:

```text
user_settings.yaml
```

without modifying source code.

Invalid settings are rejected clearly.

## Croatian Kid UI

Every child-facing screen is Croatian.

No accidental English UI.

## Calibration

Operator can:

```text
capture P0
capture PX
capture PY
validate
save
restart system
retain calibration
```

## Teaching

Operator can teach/persist:

```text
home
safe
green destination
red destination(s)
```

## Standard game

Operator:

```text
generate
place pieces
confirm
```

Child:

```text
select coordinate
watch robot
```

Correct green selection succeeds.

Wrong selection removes actual red cube.

Configured attempts are respected.

## Challenge

Rotated origin works correctly.

Left-handed educational mapping works when enabled.

No invalid left-handed TF is created.

## Motion

Normal movement uses:

```text
PTP transit
LIN descent/lift
```

RRT* only falls back where suitable.

No accepted motion violates game joint/trajectory policy.

## Hardware failures

Do not consume child attempts.

Recover through operator UI.

## Mock mode

Full game loop works without robot.

---

# 94. Deployment

Integrate into existing Docker environment.

Requirements:

- runtime config externally mounted;
- runtime calibration externally mounted;
- taught poses externally mounted;
- logs externally accessible;
- browser UI port exposed if required;
- no image rebuild needed after calibration;
- no image rebuild needed after teaching positions;
- normal `user_settings.yaml` changes should require at most application restart, not rebuild.

Prefer hot-reload of safe UI/game configuration if easy, but it is not required for MVP.

---

# 95. Configuration documentation

Create:

```text
docs/configuration.md
```

For every `user_settings.yaml` property document:

- meaning;
- units;
- default;
- allowed range;
- whether application restart is required;
- whether physical recommissioning is required.

Example:

```text
cube.size_m

Meaning:
Physical cube dimensions.

Default:
0.06 × 0.06 × 0.06 m

Requires physical recommissioning:
YES

Affects:
collision geometry
grasp position
adjacency clearance
```

This documentation is mandatory.

---

# 96. Other documentation

Create:

```text
README.md

docs/
  architecture.md
  coordinate_systems.md
  calibration.md
  configuration.md
  commissioning.md
  operator_guide.md
  troubleshooting.md
```

---

# 97. Normal exhibition workflow

Standard mode:

```text
1. Start application.

2. Readiness check.

3. Select Standard mode.

4. Press Generate.

5. Operator sees generated board.

6. Operator manually places:
   - origin piece
   - red cubes
   - green cube.

7. Press:
   Pieces placed correctly.

8. Software performs preflight.

9. Kid UI shows in Croatian:

   Na kojim se koordinatama nalazi blago?

10. Child selects coordinate.

11. UI locks.

12. UI says:

    Robot provjerava tvoj odgovor...

13. Robot picks selected cube.

14a. Green:
     success screen.

14b. Red:
     cube removed;
     remaining attempts shown.

15. Round ends.

16. Operator manually resets board.

17. New game.

18. Repeat.
```

---

# 98. Important implementation rules

Never mix:

```text
game correctness
```

with:

```text
robot execution success
```

Never mix:

```text
game coordinates
grid coordinates
base_link coordinates
```

Never calculate coordinate answers independently in frontend.

Never allow:

```text
browser -> raw robot driver
```

Required logical chain:

```text
UI
 |
 v
UI gateway
 |
 v
game manager
 |
 v
motion executor
 |
 v
MoveIt / gripper
 |
 v
hardware
```

---

# 99. Naming

Prefer explicit names:

```text
grid_cell
origin_cell
game_coordinate
grid_frame
game_origin_frame
green_cube_id
target_cube_id
```

Use units in configuration names:

```text
cell_size_m
angle_deg
clearance_m
duration_seconds
```

Avoid ambiguous names.

---

# 100. Code quality

Requirements:

- typed models;
- enums for state/mode/errors;
- no magic physical constants;
- central coordinate mathematics;
- central configuration;
- no duplicated game logic;
- no raw driver calls from UI;
- clear structured errors;
- defensive validation;
- tests for hardware-independent logic;
- readable comments describing frame conventions;
- existing repository formatters/linters respected.

---

# 101. First action for Codex

Before integration work, inspect the project and write a short implementation inventory containing:

```text
ROS packages found
Docker layout
robot model
base frame
MoveIt planning frame
MoveIt planning group
TCP/end-effector link
controllers
configured planning pipelines
Pilz availability/configuration
actual RRT* planner ID
Robotiq command interface
Robotiq feedback interface
factory calibration setup
persistent-volume strategy
existing relevant config files
```

Then map existing interfaces into this architecture.

Do not ask the user to repeat information already specified here.

If a low-level identifier can be discovered from the repository, discover it instead of asking.

---

# 102. Recommended implementation phases

## Phase 1

Repository/system inventory.

## Phase 2

Configuration framework:

```text
user_settings.yaml
robot_commissioning.yaml
runtime data schemas
```

## Phase 3

Pure game core:

```text
coordinate transforms
round generation
difficulty logic
state machine
tests
```

## Phase 4

Calibration.

## Phase 5

Mock robot executor.

## Phase 6

Croatian Kid UI + Operator UI.

## Phase 7

MoveIt/Pilz motion layer.

## Phase 8

Planning scene and gripper.

## Phase 9

RRT* fallback.

## Phase 10

Physical commissioning.

## Phase 11

Exhibition polish.

---

# 103. Final design goal

For the child, the system should feel extremely simple:

```text
Vidim koordinatni sustav.

Razmislim gdje je kocka.

Odaberem odgovor.

Robot ode upravo tamo.
```

For a very small child:

```text
Vidim zelenu kocku.

Dodirnem je.

Pravi robot je uzme.
```

For the operator:

```text
Generate.

Place pieces.

Confirm.

Let child play.

Recover if necessary.

Reset.

Repeat.
```

For the software architecture:

```text
Game logic is deterministic.

Coordinate systems are explicit.

Robot motion is constrained and predictable.

Hardware failures are recoverable.

Easy settings are configurable.

Dangerous settings are separated.

Kid UI is entirely Croatian.
```

That is the intended finished system.
