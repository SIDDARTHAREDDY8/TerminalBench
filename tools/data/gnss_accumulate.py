#!/usr/bin/env python3
"""Smoke test of the data path: transform the keyframes (base_link) into the
GNSS ENU/map frame using poses interpolated from gnss_enu.tum (vrtk_link poses),
composed with the URDF vrtk_link->base_link offset, voxelise and save a PLY."""
import argparse, os, time
import numpy as np
import open3d as o3d
from scipy.spatial.transform import Rotation as R, Slerp

# from itrek_frames.urdf: joint vrtk_to_base_link  parent=vrtk_link child=base_link
T_VRTK_BASE_XYZ = np.array([-0.173575, 0.0, -0.469325])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyframes", required=True)
    ap.add_argument("--traj", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--voxel", type=float, default=0.10)
    ap.add_argument("--no-urdf-offset", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    kf = np.load(a.keyframes)
    stamps = kf["stamps"]
    T = np.loadtxt(a.traj)
    ts, xyz, quat = T[:, 0], T[:, 1:4], T[:, 4:8]
    rot = R.from_quat(quat)
    slerp = Slerp(ts, rot)
    inside = (stamps >= ts[0]) & (stamps <= ts[-1])
    print(f"keyframes {len(stamps)}, {inside.sum()} inside trajectory span "
          f"[{ts[0]:.3f},{ts[-1]:.3f}] (kf {stamps[0]:.3f}..{stamps[-1]:.3f})")
    clouds = []
    for i in np.where(inside)[0]:
        st = stamps[i]
        Rw = slerp([st])[0]
        pw = np.array([np.interp(st, ts, xyz[:, k]) for k in range(3)])
        p = kf[f"points_{i}"].astype(np.float64)
        if not a.no_urdf_offset:
            p = p + T_VRTK_BASE_XYZ  # base_link -> vrtk_link (rotation identity)
        clouds.append(Rw.apply(p) + pw)
    P = np.concatenate(clouds)
    pc = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(P))
    pc = pc.voxel_down_sample(a.voxel)
    o3d.io.write_point_cloud(a.out, pc, write_ascii=False, compressed=False)
    Q = np.asarray(pc.points)
    lo, hi = Q.min(0), Q.max(0)
    print(f"accumulated {len(P)} pts -> {len(Q)} after {a.voxel} m voxel in {time.time()-t0:.1f}s; "
          f"wrote {a.out} ({os.path.getsize(a.out)/1e6:.1f} MB)")
    print(f"extents: x {lo[0]:.2f}..{hi[0]:.2f} ({hi[0]-lo[0]:.1f} m)  y {lo[1]:.2f}..{hi[1]:.2f} ({hi[1]-lo[1]:.1f} m)  "
          f"z {lo[2]:.2f}..{hi[2]:.2f} ({hi[2]-lo[2]:.1f} m)")


if __name__ == "__main__":
    main()
