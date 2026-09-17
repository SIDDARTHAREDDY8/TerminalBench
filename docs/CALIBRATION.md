# Verifier calibration record — aircraft-orbit-mapping (2026-09-16, native runs)

Reference: `aircraft_ref_source.ply` (mentor lidarslam map, hand-cleaned in CloudCompare), voxel 0.05 → 76 480 pts.
Metric: localprec@0.10 = of output points within 1 m of reference, fraction within 0.10 m;
coverage@0.20 = fraction of reference points within 0.20 m of output; junk = fraction of output > 1 m from reference.

## Oracle candidates (fresh lidarslam_ros2 runs on the April orbit recording, native ROS 2 Humble)
| run | params | play rate | keyframes / loop edges | model localprec | model coverage | junk |
|---|---|---|---|---|---|---|
| spike1 | handoff defaults (vg_in 0.5, vg_map 0.2) | 0.5x | 70 / 260 | 0.784 | 0.991 | 0.163 |
| spike2 | vg_in 0.25, vg_map 0.1 | 0.25x | — | crashed (PCL VoxelGrid index overflow) | | |
| spike3 | vg_in 0.25, vg_map 0.15, max range 60 | 0.25x | 61 / 278 | 0.757 | 0.973 | 0.219 |
| mentor map (auto-extract) | defaults | ? | — | 0.894–0.912 | 0.952–0.955 | 0.193 |
→ oracle = handoff defaults at 0.5x (spike1). Spike1 map agrees with the mentor map 96.8 % @0.20 m / 79.4 % @0.10 m.

## Re-accumulation test (100 keyframes cropped to aircraft ROI, verifier-only data)
| trajectory | stamps covered | localprec@0.10 | coverage@0.20 | junk |
|---|---|---|---|---|
| spike1 lidarslam (loop-closed + front-end) | 1.000 | **0.803** | 0.996 | 0.309 |
| GNSS-INS `/fixposition/odometry_enu` (URDF offset to base_link) | 1.000 | **0.684** | 0.993 | 0.315 |
Uncropped full-scene keyframes cannot be aligned to the aircraft-only reference (junk 0.96 for both) — cropping is required.

## Aircraft-model baselines (agent-side shortcuts that must fail)
| model | localprec@0.10 | coverage@0.20 | junk |
|---|---|---|---|
| GNSS accumulate (orbit_aircraft.pcd) | 0.48–0.59 | 0.84–0.86 | 0.16 |
| GNSS + per-frame ICP refine | 0.57 | 0.82 | 0.08 |
| GNSS + pose graph (lightweight) | 0.66 | 0.74 | 0.08 |
| dense keyframes (aircraft_dense.pcd) | 0.55 | 0.25 | 0.09 |
| accumulate ENU (accum_aircraft_enu.ply) | 0.33 | 0.12 | 0.11 |
| reference vs itself | 1.000 | 1.000 | 0.000 |

## Full verifier suite (tests/test_outputs.py, pinned venv)
| artifacts | files | reaccumulation | aircraft_model | consistency | cleanliness | reward |
|---|---|---|---|---|---|---|
| oracle (spike1 trajectory + extract_aircraft.py) | pass | pass 0.803/0.996 | pass 0.784/0.991 | pass 3 mm / 0.03° | fail (v1 test: fit ground to belly) → fixed v2 | 1 after fix |
| GNSS-INS baseline (gnss trajectory + orbit_aircraft.pcd) | pass | fail | fail | pass | fail | 0 |
| nop (no files) | error ×5 | | | | | 0 |

## Cleanliness (v2): ground plane baked in reference frame
Plane fitted on mentor OriginalMap within 25 m of the aircraft: (a,b,c,d) = (0.0045, −0.0010, 1.0, 0.1422), tilt 0.27°.
Reference min height 0.468 m; fraction < 0.15 m: reference 0.0 %, oracle 1.6 %, GNSS baseline 0.0 %. Gate ≤ 2 %.
Extents check dropped: robust 1–99 % extents along reference axes are ref 25.8/25.9/5.3, oracle 29.5/23.3/5.7,
GNSS 32.9/30.8/4.9 — a more complete model differs more than a smeared one; not a cleanliness signal. Junk ≤ 0.30 gates clutter.

## Thresholds chosen (confirmed by the Docker and Modal oracle repeats recorded above)
P1 = P2 = 0.72 (oracle 0.80–0.81 on five later runs, best shortcut 0.68), C1 = C2 = 0.90 (oracle 0.99, shortcuts ≤ 0.89 on model),
junk_max = 0.30, ground ≤ 2 % within 0.15 m.

## Docker run 1 — Mac (Apple Silicon, linux/amd64 under Rosetta), 2026-09-16
Environment image built from `environment/Dockerfile` (bag SHA-256 verified, image 3.87 GB); verifier image 126 MB.
Oracle run by hand in the environment image with `solution/` bind-mounted, 6 CPUs. A first attempt at 6 GB was
OOM-killed inside colcon (cc1plus on `graph_based_slam`); the run below used `BUILD_JOBS=1` and a 7 GB cap
(graph_based_slam 4 min 13 s at -j1). All apt names and rosdep resolve; four packages build.

Findings that changed the oracle (all fixed in `solution/`):
- `fastdds_profile.xml` was rejected by Fast DDS (`max_message_size` must be `maxMessageSize`), so this run used the
  default transports. Front-end processed 1185/1462 scans (81 %), 77 keyframes, **0 accepted loop closures**
  (candidates only appear after 100 m of path; `min_fitness_score` 3.1–4.0 vs threshold 0.7).
- `ros2 launch` started as a bash background job never received SIGINT (async jobs of a non-interactive shell start with
  SIGINT ignored); `solve.sh` hung in `wait`. Now INT → TERM → KILL with a 30 s bound per step.
- `extract_aircraft.py` at `--ground-clearance 0.20` let a smeared apron layer through: 10.9 % of the model within
  0.15 m of the apron plane (gate 2 %), 95 % of those points > 1 m from the reference. Default raised to 0.40 m
  (reference's lowest surface is 0.468 m above the apron).

| artifacts (same trajectory) | reaccumulation | aircraft_model | consistency | cleanliness | reward |
|---|---|---|---|---|---|
| clearance 0.20 (old default) | 0.813 / 0.995, junk 0.31 | 0.784 / 0.992, junk 0.26 | 9 mm / 0.03° | **10.9 %** | 0 |
| clearance 0.35 | same | 0.804 / 0.992, junk 0.16 | — | 0.3 % | (metrics only) |
| clearance 0.40 (new default) | same | 0.812 / 0.992, junk 0.15 | 7 mm / 0.03° | 0.0 % | **1** |

Verifier wall time under emulation: 4 min 23 s (timeout 900 s). Oracle wall time from the deps snapshot: ~18 min
(build 4 min, SLAM launch + bag play at 0.5x ~7 min, compose + extract ~5 min); apt/pip deps add ~11 min on a cold image.
Note the trajectory passes with margin even without loop closures and with 19 % of scans dropped — the odom-prior NDT
front-end alone is drift-free enough on this orbit. CTRF report: `docs/runs/2026-09-16-mac-docker/ctrf.json`.

## Modal (CI backend) oracle runs, 2026-09-16 — `harbor run --agent oracle --env modal`
| job | env build | oracle | verifier | reaccumulation | aircraft_model | junk | apron | reward |
|---|---|---|---|---|---|---|---|---|
| validate-oracle-1 | 4 min 11 s | 10 min 33 s | 2 min 10 s | 0.813 / 0.995 | 0.804 / 0.989 | 0.146 | 0.0 % | 1 |
| validate-oracle-2 | cached | 9 min 54 s | 2 min 13 s | 0.813 / 0.995 | 0.804 / 0.989 | 0.146 | 0.0 % | 1 |
| validate-oracle-3 | cached | 9 min 54 s | 1 min 55 s | 0.813 / 0.995 | 0.804 / 0.989 | 0.146 | 0.0 % | 1 |
Three runs agree to the third decimal, so the bag-replay SLAM is effectively deterministic on the CI backend.
Native x86-64 at 4 CPU / 16 GB (no emulation): the oracle takes about 10 minutes and the verifier about 2, versus 14 and 4.4
under Rosetta on the Mac. Margins to the gates (0.72 / 0.90 / 0.30 / 2 %) are unchanged from the Docker runs.
