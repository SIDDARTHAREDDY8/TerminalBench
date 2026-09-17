# Data tooling report — aircraft-orbit-mapping (2026-09-16)

Source bag: `<source recording>.mcap` (ground-robot sensor bag, 2026-04-01)
(6.54 GB on disk, 14.82 GB uncompressed, 9376 zstd chunks, profile `ros2`, written by libmcap 0.8.0,
rosbag2 metadata record `{ROS_DISTRO: humble}`; 109 029 messages, 147.48 s,
2026-04-01 16:50:36.892 → 16:53:04.368 UTC-4).

Environment: ROS 2 **Humble is installed** (`/opt/ros/humble`, `ros2` on PATH, rosbag2 mcap plugin works).
Python: mcap 1.4.0, mcap_ros2 0.5.7, numpy 1.26.4, scipy 1.8.0 (prints a numpy-version warning, harmless),
open3d 0.17.0. Disk: 2.0 GB free at the end; total written by this work: **107 MB** in `scratch/data/`.

All tools stream the bag read-only (one pass each, 2–17 s per pass).

## 1. trim_mcap.py — validated on a 5 s slice

```
python3 tools/data/trim_mcap.py --in <bag>.mcap --out scratch/data/orbit_slice5s.mcap \
  --topics /hesai/points /livox/lidar /fused_points /fixposition/odometry_enu /fixposition/odometry_llh \
           /fixposition/poiimu /fixposition/fpa/corrimu /odometry/wheels /tf /tf_static \
  --start-sec 0 --duration-sec 5
```
Copies schemas, channels (with `offered_qos_profiles` metadata), messages (log_time, publish_time, sequence
preserved verbatim), metadata records and attachments; writer = `mcap.writer.Writer(compression=ZSTD, chunk_size=4 MiB)`.
`--start-sec` is relative to the first message; omit both time flags for the full bag.

Verification of the slice (mcap reader):
- per-topic counts of source window == slice: `/tf_static 62, /tf 1278, /hesai/points 50, /livox/lidar 152,
  /fixposition/odometry_enu 49, /fixposition/fpa/corrimu 965, /fixposition/odometry_llh 48, /fixposition/poiimu 47,
  /odometry/wheels 220, /fused_points 37` (2908 msgs) — identical set of (topic, log_time, publish_time, sequence, len).
- slice header profile `ros2`; 47 chunks all `zstd`; 6 schemas; every channel keeps `offered_qos_profiles`; metadata `rosbag2 {ROS_DISTRO: humble}` copied.
- `ros2 bag info -s mcap scratch/data/orbit_slice5s.mcap` → Bag size 79.2 MiB, Duration 4.999 s, 2908 messages, all 10 topics with the counts above.
- Slice: 240.9 MB payload → 83.0 MB on disk (**ratio 0.345**).

The full trimmed bag was NOT produced (disk). Estimate below.

### Per-topic byte totals, full bag (streamed once, `bag_stats.py`, 16.6 s)

| topic                          |   msgs | payload MB | est. zstd MB | rate Hz |  span s |
|--------------------------------|--------|------------|--------------|---------|---------|
| /hesai/points                  |   1475 |     2761.5 |       1217.1 |   10.00 |   147.4 |
| /fused_points                  |   1462 |     2666.8 |       1175.4 |   10.00 |   146.1 |
| /camera_01/depth/points        |   1468 |     2513.7 |       1107.9 |    9.99 |   146.8 |
| /livox/lidar                   |   4408 |     2293.3 |       1010.8 |   29.92 |   147.3 |
| /camera_02/color/image_raw     |   1474 |     1132.1 |        499.0 |    9.99 |   147.4 |
| /camera_01/color/image_raw     |   1468 |     1127.5 |        497.0 |    9.99 |   146.8 |
| /camera_02/depth/image_raw     |   1474 |      754.8 |        332.7 |    9.99 |   147.4 |
| /camera_01/depth/image_raw     |   1468 |      751.7 |        331.3 |    9.99 |   146.8 |
| /camera_02/left_ir/image_raw   |   1474 |      377.5 |        166.4 |    9.99 |   147.4 |
| /camera_01/left_ir/image_raw   |   1468 |      375.9 |        165.7 |    9.99 |   146.8 |
| /camera_02/depth/points        |    574 |       31.8 |         14.0 |    3.98 |   143.8 |
| /fixposition/fpa/corrimu       |  29632 |        9.7 |          4.3 |  201.21 |   147.3 |
| /tf                            |  37933 |        5.6 |          2.5 |  257.21 |   147.5 |
| /odometry/wheels               |   7344 |        5.3 |          2.3 |   50.00 |   146.9 |
| /diagnostics                   |   2376 |        5.1 |          2.3 |   16.14 |   147.2 |
| /fixposition/fpa/odomenu       |   1473 |        1.1 |          0.5 |   10.00 |   147.2 |
| /fixposition/odometry_enu      |   1474 |        1.1 |          0.5 |   10.00 |   147.3 |
| /tf_static                     |   1755 |        0.6 |          0.3 |   11.90 |   147.4 |
| /camera_0x/*/camera_info (×4)  | 4×~1470|     4×0.6  |       4×0.3  |    9.99 |   147   |
| /fixposition/poiimu            |   1472 |        0.5 |          0.2 |   10.00 |   147.1 |
| /fixposition/odometry_llh      |   1473 |        0.2 |          0.1 |   10.00 |   147.2 |
| **TOTAL**                      | 109029 |    14818.3 |       6531.2 |         |         |

("est. zstd" uses the bag-wide ratio 0.441.) `/fixposition/fpa/gnsscorr` and `/fixposition/fpa/tp` have 0 messages.

**Spec subset** (10 topics): payload **7 744.6 MB** (52.3 % of the bag).
Estimated trimmed size: **≈ 2.67 GB** using the measured slice ratio 0.345 (point-cloud-only content compresses
better than the bag average), or 3.41 GB at the bag-wide ratio 0.441. Expect ~2.7 GB; needs ≥ 3 GB free to write.

## 2. extract_keyframes.py — `/fused_points`

```
python3 tools/data/extract_keyframes.py --in <bag>.mcap --out scratch/data/keyframes.npz   # defaults: --n 100 --range 45 --voxel 0.05 --ground-margin 0.20
```
- frame_id **`base_link`**; fields `x@0 y@4 z@8` all FLOAT32, `point_step 12`, height 1, `is_dense False`, little-endian, no NaNs seen.
- 1462 msgs, **151 472–152 256 points/msg** (median 151 968); header-stamp span 1775076638.101 → 1775076784.202
  (**146.10 s**), **10.00 Hz**, dt median 100.0 ms / max 118.5 ms, monotonic. First /fused_points is 1.2 s after bag start.
  log_time − header.stamp ≈ 116 ms (fusion latency).
- Ground: histogram (2 cm bins) of the lowest 40 % of z over the 100 frames (≤ 45 m) → dominant bin **ground_z = −0.160 m**
  in base_link (URDF base_footprint is at −0.1524 m — consistent); 38.6 % of in-range points lie within ±10 cm of it. Kept z > −0.160+0.20 = +0.04 m.
- Picked 100 stamps evenly spaced by message index (gap 1.39–1.51 s). Per frame: ~145 k in range → ~55 % non-ground → 0.05 m voxel →
  **3 994 / 10 907 / 18 873 (min/median/max) points**, 1 127 949 total.
- `scratch/data/keyframes.npz` = **13.6 MB** (plain `np.savez`, float32) — no downgrade to 0.08 m needed.
  Keys: `stamps` float64 (100,), `points_0..points_99` float32 (N,3), `frame_id` = "base_link", `ground_z` float,
  plus provenance `range_m`, `voxel_m`, `ground_margin_m`.
- Caveats: the z-threshold ground drop is done in base_link, so robot pitch/roll × range leaks some far ground in (the
  0–0.5 m z band still holds ~40 % of in-range points) and a few stray sky/noise points reach z = 60–75 m within 45 m xy
  range (livox artefacts). The verifier's reference keyframes should be cropped to the aircraft region anyway.
  The 5-LiDAR fused cloud is very redundant near the robot: 78.7 k non-ground raw → 4.3 k voxels in one slice frame.

## 3. extract_gnss_traj.py — `/fixposition/odometry_enu`

```
python3 tools/data/extract_gnss_traj.py --in <bag>.mcap --out scratch/data/gnss_enu.tum
```
- **1474 poses**, frame_id **`map`** → child **`vrtk_link`** (so this is the VRTK antenna/POI body, NOT base_link;
  base_link = vrtk_link ⊕ URDF offset (−0.1736, 0, −0.4693) m, identity rotation). `map` sits on `FP_ENU0` (identity static TF)
  → it is the Fixposition local ENU frame. Position z ≈ −0.3…+0.07 m ⇒ ENU origin is at ground level near the start.
- header-stamp span 1775076637.000 → 1775076784.300 (147.30 s), **10.00 Hz** exactly (dt = 100.0 ms, no duplicates),
  log_time − header.stamp median 4.2 ms.
- xy bbox x −72.5…−31.6, y −4.4…31.1. **Circle fit (Kasa): centre (−51.06, 12.89), radius 16.79 m**, residual rms 2.55 m,
  max 6.7 m (the orbit is not a clean circle: r varies 12.4–21.8 m, moving-only fit gives the same centre/r=16.77).
  Angle swept about the centre: **352.5°** (one full orbit). Total path length **124.08 m** (1.18 × circumference).
  Speed median 0.84 m/s, max 2.2 m/s, 4 % stationary.
- Heading (yaw) does not follow the direction of travel (4-wheel-steer platform crabs; yaw swings −178…+138°).
- Pose covariance diag median (x y z r p y) = [0.00145 0.00274 0.00216 0.00025 0.000595 0.0002];
  yaw σ ≈ 0.81° → ≈ 24 cm 1σ smear at 17 m lever arm (matches the spec's "GNSS heading noise × lever arm" argument).
- Output `scratch/data/gnss_enu.tum` (148 KB), header comment line then `t x y z qx qy qz qw`, t = header.stamp.
  Also `/fixposition/odometry_llh` frame_id `vrtk_link`, status 2 (RTK fixed), lat 42.663 / lon −83.427 / alt 264.6 m.
  `/odometry/wheels` is `odom`→`base_link` with pose fixed at 0 and cov 1e6 (twist only).

## 4. TF content (`inspect_tf.py`) vs. handoff claim — CONFIRMED

```
python3 tools/data/inspect_tf.py --in <bag>.mcap      # full table in scratch/data/tf_pairs.md
```
`/tf` (37 933 msgs, 257 Hz): `FP_ECEF→FP_POI` (10 Hz), `FP_POI→FP_IMUH` (200 Hz), `FP_POI→FP_POISH`, `map→odom`, `odom→vrtk_link` (10 Hz),
`base_link→wheel_{1..4}_steer_link`, `wheel_i_steer_link→wheel_i_wheel_link` (16 Hz).
`/tf_static` (1755 msgs — re-published ~12 Hz by the Fixposition driver): `FP_ECEF→FP_ENU0`, `FP_ENU0→map` (identity),
`FP_POI→FP_VRTK` (identity), `FP_VRTK→FP_CAM`, and the camera-internal chains `camera_0x_link→depth_frame→{color,left_ir}_frame→*_optical_frame` (once each).

Frames present: FP_CAM FP_ECEF FP_ENU0 FP_IMUH FP_POI FP_POISH FP_VRTK base_link camera_01_* camera_02_* map odom vrtk_link wheel_*.
**Absent: `hesai`, `livox_frame`, `livox_frame_{front,rear,left,right}`, `livox_{front,rear,left,right}`, `vrtk_link→base_link`, `base_link→camera_0x_link`, `FP_POI→base_link`.**
`base_link` appears only as the parent of the wheel joints, `vrtk_link` only as child of `odom` — the two subtrees are disconnected.
So the handoff guide is correct: the bag lacks the sensor mounts and needs the URDF (robot_state_publisher) to connect
`odom→vrtk_link→base_link→{hesai, livox_*, camera_0x_link}`.

Note: `/livox/lidar` messages carry frame_ids `livox_frame_front/rear/left/right` (38 each per 5 s, 4 sensors interleaved on one topic),
while the URDF names the links `livox_front/rear/left/right` (+ a `livox_frame` at base_link identity). That naming mismatch
matters only if someone maps raw /livox/lidar; `/fused_points` is already in base_link.

### `itrek_frames.urdf` (robot `i-trek`, mesh-free) — fixed joints
| joint | parent → child | xyz (m) | rpy (rad) |
|---|---|---|---|
| vrtk_to_base_link | **vrtk_link → base_link** | −0.173575 0 −0.469325 | 0 0 0 |
| itrek_lidar_hesai_to_base_link | base_link → hesai | 0 0 0.543964 | 0 0 1.5708 |
| livox_frame_to_base_link | base_link → livox_frame | 0 0 0 | 0 0 0 |
| itrek_livox_front_to_base_link | base_link → livox_front | 0.428808 0 0.365184 | −0.872665 0 −1.5708 |
| itrek_livox_rear_to_base_link | base_link → livox_rear | −0.428808 0 0.365184 | −0.872665 0 1.5708 |
| itrek_livox_left_to_base_link | base_link → livox_left | 0 0.349484 0.355127 | −0.872665 0 0 |
| itrek_livox_right_to_base_link | base_link → livox_right | 0 −0.349484 0.355127 | 0.872665 0 0 |
| base_link_to_camera_01_link | base_link → camera_01_link | 0.453676 0.04755 0.282290 | 0 −0.034907 0 |
| camera_01_optical_joint | camera_01_link → camera_01_rgb_optical_frame | 0 | −1.5708 0 −1.5708 |
| base_link_to_camera_02_link | base_link → camera_02_link | 0.345673 0.04755 0.371726 | 0 −1.0472 0 |
| camera_02_optical_joint | camera_02_link → camera_02_rgb_optical_frame | 0 | −1.5708 0 −1.5708 |
| navsat_joint | base_link → FP_POI | 0.2 0 0.3 | 0 0 0 |
| base_link_to_charge_plug_front/rear | base_link → charge_plug_front/rear | ±0.508 0 0.20 | 0 0 {0, π} |
| base_footprint_joint | base_link → base_footprint | 0 0 −0.1524 | 0 0 0 |
| wheel_{1..4}_steer_joint (revolute, z) | base_link → wheel_i_steer_link | (±0.3048, ±0.3048, −0.0254) | 0 |
| wheel_{1..4}_drive_joint (continuous, y) | wheel_i_steer_link → wheel_i_wheel_link | 0 | — |
Plus a `ros2_control` gz block (irrelevant offline). Links: hesai, livox_frame, livox_front/rear/left/right, camera_01_link,
camera_01_rgb_optical_frame, camera_02_link, camera_02_rgb_optical_frame, vrtk_link, FP_POI, charge_plug_front/rear, base_footprint, base_link, wheel_*.
Inconsistency worth knowing: URDF has base_link→FP_POI = (0.2, 0, 0.3) but also vrtk_link→base_link = (−0.17, 0, −0.47) while the
bag says FP_POI→FP_VRTK is identity — the two GNSS lever arms disagree by ~(0.03, 0, 0.17) m; only the vrtk chain is needed for the odom prior.

## 5. Smoke test — GNSS accumulation (`gnss_accumulate.py`)

```
python3 tools/data/gnss_accumulate.py --keyframes scratch/data/keyframes.npz --traj scratch/data/gnss_enu.tum --out scratch/data/gnss_accum.ply
```
Pose at each keyframe stamp: linear xyz interp + Slerp on the 10 Hz `map→vrtk_link` poses (all 100 stamps inside the span),
points moved base_link→vrtk_link by the URDF offset, then into `map`(ENU). 1 127 949 pts → **642 177 after 0.1 m voxel**,
`scratch/data/gnss_accum.ply` = **15.4 MB** (binary, double xyz, Open3D).
Extents: x −117.5…8.9 (126.4 m), y −45.9…72.3 (118.2 m), z −1.80…88.6 m (90 m — 377 stray points above 20 m; the
45 m range ring around the orbit explains the 120 m footprint). Within 20 m of the orbit centre (−51.1, 12.9): 142 k points,
bbox 39.8 × 40.0 × 12.9 m, z mass in 0–4 m with a tail to 8 m — an aircraft-sized blob is where the orbit centre says it should be.
This only proves the data path (stamps ↔ poses ↔ frames); it is the naive baseline the verifier must reject.

## Files
- tools (`tools/data/`): `trim_mcap.py`, `bag_stats.py`, `inspect_tf.py`, `extract_keyframes.py`, `extract_gnss_traj.py`, `gnss_accumulate.py`, this `REPORT.md`
- data (`scratch/data/`, 107 MB): `orbit_slice5s.mcap` 83.0 MB, `keyframes.npz` 13.6 MB, `gnss_accum.ply` 15.4 MB, `gnss_enu.tum` 148 KB,
  `bag_stats.txt`, `tf_pairs.md`, `gnss_report.txt`, `keyframes_report.txt`, `accum_report.txt`
Nothing committed (scratch/ is gitignored; the project dir is not a git repo).
