# instruction.md fact sheet — aircraft-orbit-mapping

Raw material for the hand-written `tasks/aircraft-orbit-mapping/instruction.md`.
Every bullet is a fact the instruction may state; nothing here describes a method.
Numeric thresholds are the calibrated values in `tests/thresholds.json`
(natively calibrated 2026-09-16; re-confirm after the Docker oracle runs). Do not name the aircraft type.

## Inputs (all absolute paths, all read-only for the agent's purposes)

- `/app/data/orbit.mcap` — ROS 2 Humble recording (MCAP, zstd), ~147 s. A ground
  robot drove one orbit around a parked aircraft on an open apron.
- `/app/data/itrek_frames.urdf` — the robot's sensor-mount calibration (URDF, fixed
  joints), including the transforms that the recording does not contain.
- `/app/data/README.txt` — topic list, message types, frame ids, units.
- Topics in the recording: `/fused_points` (sensor_msgs/PointCloud2, `base_link`,
  10 Hz, 1462 messages, fields x y z float32), `/hesai/points`, `/livox/lidar`,
  `/fixposition/odometry_enu` (nav_msgs/Odometry, `map` → `vrtk_link`),
  `/fixposition/odometry_llh`, `/fixposition/poiimu`, `/fixposition/fpa/corrimu`,
  `/odometry/wheels`, `/tf`, `/tf_static`.
- The recording's `/tf` contains `map → odom → vrtk_link`; `vrtk_link → base_link`
  (and every other sensor mount) is only in the URDF.
- `/fused_points` header stamps: `header.stamp.sec` + `header.stamp.nanosec`
  (UNIX epoch); the verifier keys everything on these stamps.
- Working directory is `/app`; the agent runs as root with internet.

## Deliverable 1 — `/app/trajectory.tum`

- Pose of `base_link` in ONE fixed, right-handed, metric world frame of the
  agent's choosing (any origin/orientation; z need not be up).
- Exactly one line per `/fused_points` message, keyed by that message's header
  stamp; ascending time; no header line required (lines starting with `#` are
  ignored).
- Line format (TUM): `t x y z qx qy qz qw`, whitespace separated, where
  `t` = stamp in seconds (float; nanosecond digits preserved, e.g.
  `1775076638.101144075`), `x y z` in metres, `qx qy qz qw` a unit quaternion
  (x, y, z, w order) rotating vectors from `base_link` into the world frame.
- All values finite. The verifier interpolates poses at its own keyframe stamps,
  so ≥ 95 % of `/fused_points` stamps must be present (a missing stamp counts
  against coverage; extra stamps are ignored).
- Poses must be drift-free and metric: the raw scans, re-projected with these
  poses, must match the reference aircraft with local precision@0.10 m ≥ 0.72
  and coverage@0.20 m ≥ 0.90 after a rigid alignment performed by the verifier
  (so the choice of world frame does not matter).

## Deliverable 2 — `/app/aircraft.ply`

- Point cloud of the aircraft and only the aircraft, in the SAME world frame as
  `/app/trajectory.tum`, metres.
- PLY, `format binary_little_endian 1.0`, one `element vertex N` with at least
  the properties `float x`, `float y`, `float z` (other properties are ignored),
  N ≥ 1, all values finite.
- Accuracy: after the verifier's rigid alignment to its reference,
  local precision@0.10 m ≥ 0.72 and coverage@0.20 m ≥ 0.90.
- Cleanliness: at most 2 % of the points may lie within 0.15 m of the apron
  surface (the ground plane under the aircraft); at most 30 % of the points may
  lie farther than 1.0 m from the true aircraft surface (no ground, cones,
  vehicles, buildings or robot self-returns).
- Consistency: the cloud must be in the trajectory's frame — its centroid must
  lie within 0.5 m and its heading (long axis) within 3° of the aircraft as
  re-projected from the raw scans with the agent's own trajectory.

## Definitions the instruction may use

- local precision@0.10 m: of the agent's points that lie within 1.0 m of the
  reference aircraft surface, the fraction that lie within 0.10 m of it (a
  smeared or drifting reconstruction thickens every surface and lowers it).
- coverage@0.20 m: fraction of reference surface points that lie within 0.20 m
  of some agent point (completeness).
- "Apron surface" / ground plane: the plane of the apron under the aircraft, as
  known to the verifier; the aircraft's lowest surface is ~0.5 m above it.
- Frame convention for `base_link`: x forward, y left, z up (REP-103).

## Constraints

- No network resources are needed; the recording and calibration in `/app/data`
  are the only inputs. Do not require a GPU (none is available).
- Both files must exist at the paths above when the agent finishes; the verifier
  runs in a separate container and reads only those two files.
- Do not mention the aircraft type, tail number, reference map, keyframe set,
  thresholds' numeric provenance, or any solver/library.

## Mandatory final line (blank line before it, newline after it)

You have 14400 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.
