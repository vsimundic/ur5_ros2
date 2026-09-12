# Phase 6 game-piece update

This Phase 6 decision supersedes the earlier red/green treasure-piece rules in
the game-mode sections of `treasure_hunt_spec.md`.  It changes the educational
content only; it does not authorize physical robot motion or alter any
commissioning requirement.

The mock/browser implementation and manual UI testing were accepted on
2026-09-12. This acceptance covers only the synthetic mock application; it is
not a physical-motion, grasping, calibration, or commissioning approval.

The exhibition set has five unique, fixed-colour pieces:

- green star;
- blue circle;
- red heart;
- black triangle; and
- white crescent.

`user_settings.yaml` requires exactly one of every colour. The fixed Spatial
origin is also user-editable there (`game.spatial.origin_column` and
`game.spatial.origin_row`). On the default 6 by 6 board it is at column 2,
row 2 (zero-based), leaving room around it for relative-direction examples.

## Easy

There is no origin frame.  The board shows five coloured pieces as cubes.  The
backend randomly chooses one colour and the child UI displays its Croatian
colour name in neutral text.  The child selects the occupied board cell that
contains the requested colour.

## Beginner

There is no origin frame.  The board shows the five fixed-colour shapes.  The
backend randomly chooses one shape and displays its Croatian name neutrally to
the child (`Zvijezda`, `Krug`, `Srce`, `Trokut`, or `Mjesec`).
The child selects the occupied board cell containing the matching shape.

## Spatial

The fixed black-origin, red-X, green-Y frame is placed.  The five fixed-colour
shapes are randomly placed in the other cells.  The backend randomly chooses
one occupied relative location and the UI states it in Croatian, for example
`3 gore i 1 lijevo od ishodišta`.  The child selects the shape at that
location.

## Standard

Standard restores the original coordinate-pair game. Its origin is generated
within the configured central margin with zero rotation and right-handed game
coordinates. The green star is the treasure. The board displays all five
fixed-colour shapes, while the answer buttons display the five corresponding
`(x, y)` coordinate pairs. Positive values have no leading `+` sign and zero
is shown as `0`. The child selects the green star's coordinates.

## Challenge

Challenge extends the restored Standard coordinate-pair game with the
configured origin rotations and optional educational handedness. It uses the
same five shapes and `(x, y)` answer buttons, but randomly chooses any of the
five shapes as the target for each round.

Every wrong selection is an executed game selection and, only after a
successful mock/physical result, consumes one configured attempt.  This makes
the two-heart loss screen consistent in every mode. The
mock launch remains the required test target until physical pick, placement,
collision geometry, and destinations are explicitly commissioned.
