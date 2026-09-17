# run-claude-3 — the agent's own final report

tool calls: {'Bash': 10} 

Both deliverables are written and validated.

## What I built

**`/app/trajectory.tum`** — 1462 lines, one per `/fused_points` message (100 % of stamps), in the recording's ENU `map` frame.

The pose chain is `map → odom → vrtk_link` (from recorded `/tf`, identical to `/fixposition/odometry_enu`) composed with the URDF's `vrtk_link → base_link` (`xyz -0.173575 0 -0.469325`), SLERP/linear-interpolated to each scan stamp.

I validated this rather than assuming it: I built a 6.1 M-point voxel map and ran point-to-plane ICP per scan against it. Corrections came out at **3–5 mm and ~0.01°** with zero systematic bias, and the median point-to-plane residual was **0.017 m** — the GNSS-INS poses are already ground-truth quality, so refining them would only fit noise. Start-vs-end overlap (scans 0–140 vs 1320–1462) matches as well as time-adjacent scans, confirming drift-free closure. The near-zero body-frame mean correction also bounds any lidar/GNSS clock offset below ~1 ms.

I also checked for motion distortion by registering each scan's first and last azimuth quarters separately: the translation difference along the velocity direction was ~0 (±0.015 m) where skew would predict 0.08–0.16 m. The points are instantaneous at `header.stamp`, so no deskewing was needed.

**`/app/aircraft.ply`** — 948,105 points, binary little-endian PLY 1.0 with `float x/y/z`, same ENU frame.

Pipeline: accumulate all 1462 scans (71 M points in the aircraft box) → apron height field (degree-4 robust polynomial, 1 cm residual) → cut at 0.45 m above apron → filter → 26-connected components → keep the aircraft plus nearby elevated fragments → surface-growing recovery pass.

The filter was the hard part. The simulated lidar produces dense mixed-pixel artifacts — a "starburst" fan radiating from silhouette edges. Pure density thresholds deleted the horizontal stabiliser and outer wings, which are only grazed by the Livox. What worked was an occlusion-consistency test: per scan, reconstruct the exact Hesai range image from `(column, ring)` indices (I recovered the Pandar40P beam table, +14.97° to −24.81°), take a neighbourhood minimum, treat no-return rays as free space, and flag points that would have blocked a longer measurement. Combined with a voxel-occupancy count, real surfaces land at see-through ratio 0.00–0.15 and artifacts at 0.21–0.37.

## Verification

- PLY local surface residual: p50 0.025 m, p95 0.074 m, **0.75 %** beyond 0.10 m
- Coverage of high-confidence surface at 0.20 m: **0.975–0.989**
- Minimum height above apron: **0.381 m**; 0.000 % of points within 0.15 m
- Extent 33.1 × 29.4 × 8.9 m — a T-tail business jet with rear-mounted engines, winglets and landing gear

One thing to flag: when I estimate the *raw-scan* precision metric using my own cloud as a stand-in reference, I get 0.53–0.67 rather than ≥0.72. Breaking it down, points clearly on the aircraft (>0.55 m above apron) are **98.1 %** within 0.10 m — the shortfall is entirely apron points and mixed-pixel curtains that fall within 1.0 m of the aircraft's low structure (the landing gear reaches near the apron, so the ground beneath it enters the window). That is a property of the sensor data and the reference geometry, not of the poses, and it is not something a better trajectory can change. My stand-in reference is also not the hidden one, so the real figure may differ; I'm reporting the estimate as measured rather than assuming it away.

Scratch data is in `/app/work` (6.6 GB) if you want to re-run any stage; say the word and I'll clear it.
