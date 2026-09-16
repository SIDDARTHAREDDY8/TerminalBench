#!/usr/bin/env python3
"""Write the Fixposition GNSS-INS trajectory (/fixposition/odometry_enu) as TUM
`t x y z qx qy qz qw` (header stamps) and report pose count, rate, circle fit
of the orbit, path length and frame ids.  Streams the bag read-only."""
import argparse, sys, time
import numpy as np
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory


def fit_circle(xy):
    """Algebraic (Kasa) least-squares circle fit: x^2+y^2 + a x + b y + c = 0."""
    x, y = xy[:, 0], xy[:, 1]
    A = np.column_stack([x, y, np.ones_like(x)])
    b = -(x**2 + y**2)
    (a, bb, c), *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = -a / 2, -bb / 2
    r = np.sqrt(cx**2 + cy**2 - c)
    resid = np.hypot(x - cx, y - cy) - r
    return cx, cy, r, resid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    ap.add_argument("--topic", default="/fixposition/odometry_enu")
    a = ap.parse_args()
    t0 = time.time()
    rows, frames, covs = [], set(), []
    with open(a.src, "rb") as f:
        r = make_reader(f, decoder_factories=[DecoderFactory()])
        for schema, ch, m, msg in r.iter_decoded_messages(topics=[a.topic]):
            st = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            p = msg.pose.pose.position; q = msg.pose.pose.orientation
            rows.append((st, p.x, p.y, p.z, q.x, q.y, q.z, q.w, m.log_time * 1e-9))
            frames.add((msg.header.frame_id, msg.child_frame_id))
            covs.append([msg.pose.covariance[i * 7] for i in range(6)])
    T = np.array(rows, dtype=np.float64)
    order = np.argsort(T[:, 0]); T = T[order]
    dup = np.sum(np.diff(T[:, 0]) <= 0)
    with open(a.dst, "w") as fo:
        fo.write("# TUM: t x y z qx qy qz qw  (t = header.stamp; pose = %s in frame %s)\n" % (
            "/".join(sorted({c for _, c in frames})), "/".join(sorted({p for p, _ in frames}))))
        for row in T:
            fo.write("%.9f %.6f %.6f %.6f %.9f %.9f %.9f %.9f\n" % tuple(row[:8]))
    n = len(T)
    span = T[-1, 0] - T[0, 0]
    dt = np.diff(T[:, 0])
    seg = np.linalg.norm(np.diff(T[:, 1:4], axis=0), axis=1)
    cx, cy, rad, resid = fit_circle(T[:, 1:3])
    cov = np.array(covs)
    lag = T[:, 8] - T[:, 0]
    print(f"read {n} poses from {a.topic} in {time.time()-t0:.1f}s -> {a.dst}")
    print(f"  frame_id/child_frame_id pairs: {sorted(frames)}")
    print(f"  header-stamp span: {T[0,0]:.3f} .. {T[-1,0]:.3f} s  ({span:.2f} s), rate {(n-1)/span:.2f} Hz, "
          f"dt median {np.median(dt)*1e3:.1f} ms, max {dt.max()*1e3:.1f} ms, non-increasing stamps: {dup}")
    print(f"  log_time - header.stamp: median {np.median(lag)*1e3:.1f} ms, max {lag.max()*1e3:.1f} ms")
    print(f"  xyz min {T[:,1:4].min(0).round(3)}  max {T[:,1:4].max(0).round(3)}")
    print(f"  circle fit (xy): centre ({cx:.3f}, {cy:.3f}), radius {rad:.3f} m, "
          f"residual rms {np.sqrt(np.mean(resid**2)):.3f} m, max |resid| {np.abs(resid).max():.3f} m")
    print(f"  total path length {seg.sum():.2f} m (= {seg.sum()/(2*np.pi*rad):.2f} orbits of the fitted circle); "
          f"z range {T[:,3].min():.3f}..{T[:,3].max():.3f} m")
    print(f"  pose covariance diag (x y z r p y) median {np.median(cov,0).round(6)}, max {cov.max(0).round(5)}")
    print(f"  yaw sigma from cov: median {np.degrees(np.sqrt(np.median(cov[:,5]))):.3f} deg -> lever-arm smear at 17 m: "
          f"{17*np.sqrt(np.median(cov[:,5]))*100:.1f} cm (1 sigma)")


if __name__ == "__main__":
    main()
