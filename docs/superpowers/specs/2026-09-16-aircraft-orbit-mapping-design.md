# aircraft-orbit-mapping — Terminal-Bench 3 task design

Date: 2026-09-16 · Author: Siddartha Reddy Chinthala · Status: approved

## Goal
One original TB3 task for the Klavis Founding Engineer assessment. Must pass all TB3 CI
checks (22 static checks, 35-criterion rubric, Docker build, oracle = 1.0, nop = 0), fail
3/3 trials for claude-code/opus-5(max) and codex/gpt-5.6-sol(xhigh), and score 0 on both
/cheat trials. Deliver a public GitHub repo with task, commands, configs, results and
failure analysis within 7 days (by 2026-09-23).

## Task
A ground robot orbited a parked business jet (business jet; type and registration NOT disclosed to the agent) on an open apron at ~16 m radius, recording 5 LiDARs (Hesai Pandar40P + 4 Livox
Mid-360, plus the fused cloud), Fixposition GNSS-INS, IMU, wheel odometry and TF. The agent
must produce a metric, drift-free model of the aircraft.

Why it is hard for a good reason (all measured, see scratch/baselines):
- Open apron has too few LiDAR features: scan-to-scan odometry (KISS-ICP) loses tracking.
- GNSS-INS heading noise × 17 m lever arm smears every naive accumulation: precision@20cm
  of GNSS accumulate 0.55, +ICP refine 0.66, +pose graph 0.71 vs a loop-closed reference.
- The fuselage is a smooth cylinder (ICP slides along its axis); wings are thin grazing
  surfaces; the fix needs correctly configured loop-closed SLAM with the right sensor TFs.
- The agent cannot see the reference, so it cannot tell "looks like a jet" from "passes".

## Agent environment
- `FROM ros:humble-ros-base`; apt: rosbag2-storage-mcap, build tools; pip (pinned):
  numpy, scipy, open3d, mcap, mcap-ros2-support.
- `/app/data/orbit.mcap` — April 2026 orbit recording, trimmed to: /hesai/points, /livox/lidar,
  /fused_points, /fixposition/{odometry_enu,odometry_llh,poiimu,fpa/corrimu},
  /odometry/wheels, /tf, /tf_static. Downloaded at image build from a public Hugging Face
  dataset with sha256 verification (files > 100 MB are not committed).
- `/app/data/itrek_frames.urdf` — robot sensor-mount calibration.
- `/app/data/README.txt` — topics, frames, units. No solver, no hints.

## Deliverables (agent)
1. `/app/trajectory.tum` — pose of `base_link` in one fixed world frame at every
   `/fused_points` header stamp; TUM format `t x y z qx qy qz qw`, one line per stamp.
2. `/app/aircraft.ply` — the aircraft and only the aircraft, metres, same world frame.

## Verifier (separate container, `tests/`)
Baked into the verifier image: `reference/aircraft_ref.ply` (mentor-built lidarslam map,
hand-cleaned in CloudCompare; extents 28.9×29.0×7.8 m vs published G-V 28.5/29.4/7.9 m),
`reference/keyframes.npz` (~100 raw /fused_points keyframes cropped to the aircraft region,
with stamps), thresholds.json. pytest (pytest==9.1.1, pytest-json-ctrf==0.5.2) → CTRF at
/logs/verifier/ctrf.json; reward 1 iff every test passes else 0.
Tests:
- test_files: both artifacts exist, parse, finite, trajectory covers ≥ 95 % of keyframe stamps.
- Metric (calibrated 2026-09-16 on a fresh native lidarslam run + all baselines): plain
  precision@0.20 does not separate (0.85–0.90 for everything: raw maps hold real objects
  near the aircraft that the hand-cleaned reference lacks). Use instead
  localprec@0.10 = fraction of output points within 1.0 m of the reference that are within
  0.10 m of it (SLAM 0.79–0.89 vs baselines 0.57–0.66), coverage@0.20 (SLAM 0.94–0.96 vs
  baselines 0.74–0.89) and a loose junk gate (points > 1.0 m from reference ≤ 30 %).
- test_reaccumulation: keyframes transformed by interpolated agent poses → robust global
  alignment (yaw sweep + ICP) to reference → localprec@0.10 ≥ P1, coverage@0.20 ≥ C1.
- test_aircraft_model: aircraft.ply aligned to reference → localprec@0.10 ≥ P2,
  coverage@0.20 ≥ C2, junk ≤ 0.30.
- test_consistency: aircraft.ply centroid/heading agree with the re-accumulated aircraft
  in the agent's own world frame (≤ 0.5 m, ≤ 3°).
- test_cleanliness: ≤ 2 % of aircraft.ply points within 0.15 m of the fitted ground plane;
  bounding-box extents within ±1.0 m of reference.
Thresholds are calibrated: oracle passes with margin on repeated runs; all measured naive
baselines fail. Spike 1 (default params, 0.5x play): 70 keyframes, 260 loop edges, map agrees
with mentor map 97 % @0.20 m / 79 % @0.10 m. Verifier never executes agent code (data only).

## Oracle (`solution/`)
`solve.sh` builds lidarslam_ros2 (pinned vendored tarball) in a colcon
workspace, launches frames.launch.py (URDF TFs) + scanmatcher/graph_based_slam with
/fused_points, plays the bag, records loop-closed keyframe path + front-end odometry,
composes the full base_link trajectory, saves the map, extracts the aircraft (ground RANSAC
+ largest cluster near the orbit centre) → writes both deliverables. ~15–20 min, genuine
computation. Spike gate: fresh lidarslam run must beat thresholds with margin before build.

## task.toml
artifacts = ["/app/trajectory.tum", "/app/aircraft.ply"]; category "Science",
subcategory "Robotics"; verifier separate, timeout 900; agent timeout 14400;
build_timeout 3600, cpus 4, memory 16384, storage 40960, gpus 0; no allow_internet key.

## Hand-written (human) files
instruction.md, README.md sections (Difficulty / Solution / Verification explanation,
Relevant experience), PR-template answers in RESULTS.md.

## Trials & documentation
Exact CI defaults (.github/harbor-run-defaults.yml): 3 trials each of
claude-code anthropic/claude-opus-5 --ak reasoning_effort=max (env
CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000) and codex openai/gpt-5.6-sol --ak
reasoning_effort=xhigh; /cheat: 1 each with "Do not cheat…" stripped and
docs/prompts/hack-trial-prompt.md appended; harbor analyze -m sonnet on all jobs.
Repo docs: RESULTS.md (commands, configs, reward table, timings), FAILURE_ANALYSIS.md,
CHEAT_ANALYSIS.md, CHECKS.md (static, rubric, oracle, nop outputs).

## Risks
- Oracle margin (lidarslam re-run vs reference) — spike first; fallback: multi-pass NDT
  refinement, never lowering thresholds below baselines.
- Agents solving it (lidarslam_ros2 is public) — accepted; measured by the trials.
- 6 GB bag download in CI — trimmed to ~3 GB, hosted on HF, build timeout 3600 s.
- Disk on dev machine (≈1 GB free) — must free ≥ 40 GB before any Docker work.
