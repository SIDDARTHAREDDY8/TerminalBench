# tools/

Reproducibility tooling. Nothing here ships inside the task; the task only needs
`tasks/aircraft-orbit-mapping/`.

## data/ — how the task data was produced (Linux box with ROS 2 Humble + python 3.10)
| script | purpose |
|---|---|
| `bag_stats.py` | per-topic message/byte table of the source recording |
| `trim_mcap.py` | copies selected topics of a ROS 2 MCAP verbatim into a new zstd-chunked MCAP → `orbit.mcap` (see `docs/data_provenance.md`) |
| `inspect_tf.py` | lists the `/tf_static` + `/tf` parent→child pairs in the bag (shows the sensor mounts are missing → URDF ships with the task) |
| `extract_keyframes.py` | 100 evenly spaced `/fused_points` keyframes, ground removed, 0.05 m voxels, base_link frame |
| `crop_keyframes.py` | crops those keyframes to the aircraft region using verifier-side ground-truth poses → `tests/reference/keyframes.npz` |
| `extract_gnss_traj.py` | GNSS-INS trajectory as TUM (the shortcut baseline the verifier must reject) |
| `gnss_accumulate.py` | smoke test: accumulates keyframes with GNSS poses |

## calibration/
| script | purpose |
|---|---|
| `test_verify_lib.py` | 27 unit tests for the verifier library (synthetic rotations/translations, interpolation, metrics, apron plane). Run: `python -m pytest tools/calibration/test_verify_lib.py` with numpy/scipy/plyfile/pytest installed (same pins as `tests/Dockerfile`). |
| `calibrate_thresholds.py` | scores the recorded shortcut baselines with the verifier's own metric (needs open3d for .pcd input) |

Results: `docs/CALIBRATION.md`.
