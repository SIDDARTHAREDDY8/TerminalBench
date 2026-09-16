# Verifier calibration record — aircraft-orbit-mapping (2026-09-16, native runs)

Reference: `N55FV-Final.ply` (mentor lidarslam map, hand-cleaned in CloudCompare), voxel 0.05 → 76 480 pts.
Metric: localprec@0.10 = of output points within 1 m of reference, fraction within 0.10 m;
coverage@0.20 = fraction of reference points within 0.20 m of output; junk = fraction of output > 1 m from reference.

## Oracle candidates (fresh lidarslam_ros2 runs on the April N55FV bag, native ROS 2 Humble)
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
| accumulate ENU (N55FV_accum_aircraft_enu.ply) | 0.33 | 0.12 | 0.11 |
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

## Thresholds chosen (pending Docker oracle repeats)
P1 = P2 = 0.72 (oracle 0.78–0.80, best shortcut 0.68), C1 = C2 = 0.90 (oracle 0.99, shortcuts ≤ 0.89 on model),
junk_max = 0.30, ground ≤ 2 % within 0.15 m.
