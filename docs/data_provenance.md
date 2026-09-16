# Data provenance — `orbit.mcap`

| | |
|---|---|
| Source recording | ground-robot sensor bag recorded 2026-04-01: one orbit of a parked business jet on an open apron (commercial platform; published with permission) |
| Trim | `scratch/tools/trim_mcap.py` — copies the 10 topics below verbatim (schemas, channels, log/publish times, sequence numbers, QoS metadata, rosbag2 metadata record); zstd chunks |
| Topics kept | `/fused_points` (1462), `/hesai/points` (1475), `/livox/lidar` (4408), `/fixposition/odometry_enu` (1474), `/fixposition/odometry_llh`, `/fixposition/poiimu`, `/fixposition/fpa/corrimu`, `/odometry/wheels` (7344), `/tf` (37933), `/tf_static` (1755) |
| Topics dropped | all camera topics (`/camera_0x/*`), `/diagnostics`, `/rosout`, `/parameter_events` |
| Duration / messages | 147.475 s / 88 428 |
| Size | 2 923 440 111 bytes |
| SHA-256 | `a98bba643895dade48d3d81b50a5559d372c60c4b672f11128eb4c5463755966` |
| Hosting | public Hugging Face dataset `pinkman9/aircraft-orbit-mapping` (`BAG_URL` in `environment/Dockerfile`); the Dockerfile verifies the hash at build time |

The verifier's reference (`tests/reference/aircraft_ref.ply`) is the aircraft model built from the same
recording by an independent lidarslam run and hand-cleaned in CloudCompare by the platform's mapping lead;
`tests/reference/keyframes.npz` holds 100 evenly spaced `/fused_points` keyframes (base_link frame,
ground removed, 0.05 m voxels) cropped to the aircraft region with verifier-side ground-truth poses.
Neither file is present in the agent image.

## Oracle solver — `solution/lidarslam_ros2.tar.gz`

Upstream https://github.com/rsasaki0109/lidarslam_ros2 at commit 6213770d (2024-05-28, BSD-2-Clause)
with its `Thirdparty/ndt_omp_ros2` submodule (BSD-2-Clause), plus three small bag-replay fixes made
by the platform's engineering team and reused with permission (SensorDataQoS on the input cloud, an odom-prior
fallback when the exact-stamp TF lookup fails, and tuned NDT/voxel parameters). The full list is in
`FORK_NOTES.md` inside the tarball. SHA-256
`248f5caef2431f6a601293fcf04c84b6a13017a8a1c4da1c961a40acc13fdb6e`. The tarball is vendored
(not cloned at solve time) so the oracle is pinned and network-independent.
