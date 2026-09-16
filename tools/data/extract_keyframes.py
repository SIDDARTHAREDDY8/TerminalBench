#!/usr/bin/env python3
"""Stream /fused_points, pick N stamps evenly spaced over the recording, and
save cropped/ground-removed/voxelised keyframes to an npz.

PointCloud2 is decoded with mcap_ros2 (header/fields/data) but the point data
is parsed directly with numpy from the declared field offsets and point_step.

npz schema: stamps (float64, N), points_<i> (float32 Mx3), frame_id (str),
ground_z (float), plus range_m / voxel_m / ground_margin_m for provenance.
"""
import argparse, sys, time
import numpy as np
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory

PF = {1: 'i1', 2: 'u1', 3: 'i2', 4: 'u2', 5: 'i4', 6: 'u4', 7: 'f4', 8: 'f8'}


def xyz_from_pc2(msg):
    """Nx3 float32 from a PointCloud2, honouring per-field offsets and point_step."""
    n = msg.width * msg.height
    buf = np.frombuffer(bytes(msg.data), dtype=np.uint8)
    end = '>' if msg.is_bigendian else '<'
    cols = []
    for name in ("x", "y", "z"):
        fl = next(f for f in msg.fields if f.name == name)
        dt = np.dtype(end + PF[fl.datatype])
        v = np.ndarray((n,), dtype=dt, buffer=buf, offset=fl.offset, strides=(msg.point_step,))
        cols.append(v.astype(np.float32))
    return np.column_stack(cols)


def voxel_down(pts, voxel):
    """Centroid voxel downsample with numpy (no open3d dependency at extract time)."""
    if len(pts) == 0:
        return pts
    idx = np.floor(pts / voxel).astype(np.int64)
    idx -= idx.min(0)
    key = (idx[:, 0] * 73856093) ^ (idx[:, 1] * 19349663) ^ (idx[:, 2] * 83492791)
    # exact grouping: sort by (ix,iy,iz)
    order = np.lexsort((idx[:, 2], idx[:, 1], idx[:, 0]))
    idx_s = idx[order]; pts_s = pts[order]
    first = np.ones(len(idx_s), dtype=bool)
    first[1:] = np.any(idx_s[1:] != idx_s[:-1], axis=1)
    grp = np.cumsum(first) - 1
    cnt = np.bincount(grp).astype(np.float32)
    sums = np.zeros((len(cnt), 3), dtype=np.float64)
    for k in range(3):
        sums[:, k] = np.bincount(grp, weights=pts_s[:, k])
    return (sums / cnt[:, None]).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    ap.add_argument("--topic", default="/fused_points")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--range", type=float, default=45.0)
    ap.add_argument("--voxel", type=float, default=0.05)
    ap.add_argument("--ground-margin", type=float, default=0.20)
    ap.add_argument("--compress", action="store_true", help="np.savez_compressed instead of np.savez")
    a = ap.parse_args()
    t0 = time.time()

    with open(a.src, "rb") as f:
        r = make_reader(f, decoder_factories=[DecoderFactory()])
        summ = r.get_summary()
        cid = next(c.id for c in summ.channels.values() if c.topic == a.topic)
        total = summ.statistics.channel_message_counts[cid]
        pick = set(np.round(np.linspace(0, total - 1, a.n)).astype(int).tolist())
        print(f"{a.topic}: {total} messages in bag; picking {len(pick)} evenly spaced")

        stamps_all, npts_all, frame_ids, fields_seen = [], [], set(), set()
        kept = []   # (stamp, pts within range)
        i = 0
        for schema, ch, m, msg in r.iter_decoded_messages(topics=[a.topic]):
            st = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            stamps_all.append(st); npts_all.append(msg.width * msg.height)
            frame_ids.add(msg.header.frame_id)
            fields_seen.add(tuple((fl.name, fl.offset, fl.datatype, fl.count) for fl in msg.fields) + (("point_step", msg.point_step),))
            if i in pick:
                p = xyz_from_pc2(msg)
                p = p[np.isfinite(p).all(1)]
                rng = np.linalg.norm(p[:, :2], axis=1)
                kept.append((st, p[rng <= a.range]))
            i += 1
    stamps_all = np.array(stamps_all); npts_all = np.array(npts_all)
    dt = np.diff(stamps_all)
    print(f"streamed in {time.time()-t0:.1f}s")
    print(f"  frame_id(s): {sorted(frame_ids)}")
    print(f"  field layouts: {fields_seen}")
    print(f"  points/msg: min {npts_all.min()} median {int(np.median(npts_all))} max {npts_all.max()}")
    print(f"  header-stamp span {stamps_all[0]:.3f} .. {stamps_all[-1]:.3f} ({stamps_all[-1]-stamps_all[0]:.2f} s), "
          f"rate {(len(stamps_all)-1)/(stamps_all[-1]-stamps_all[0]):.2f} Hz, dt median {np.median(dt)*1e3:.1f} ms max {dt.max()*1e3:.1f} ms, "
          f"non-increasing {np.sum(dt<=0)}")

    # ground height: histogram of z over the lowest points of all kept frames
    zs = np.concatenate([p[:, 2] for _, p in kept])
    low = zs[zs < np.percentile(zs, 40)]
    hist, edges = np.histogram(low, bins=np.arange(low.min(), low.max() + 0.02, 0.02))
    k = np.argmax(hist)
    ground_z = float(0.5 * (edges[k] + edges[k + 1]))
    frac_ground = np.mean(np.abs(zs - ground_z) < 0.10)
    print(f"  ground z (dominant 2 cm bin of lowest 40% of z): {ground_z:.3f} m in {sorted(frame_ids)[0]}; "
          f"{100*frac_ground:.1f}% of in-range points within +-10 cm of it")
    zthr = ground_z + a.ground_margin

    out = {"stamps": np.array([s for s, _ in kept], dtype=np.float64),
           "frame_id": np.array(sorted(frame_ids)[0]), "ground_z": np.array(ground_z),
           "range_m": np.array(a.range), "voxel_m": np.array(a.voxel), "ground_margin_m": np.array(a.ground_margin)}
    nraw, nfin = [], []
    for j, (st, p) in enumerate(kept):
        q = p[p[:, 2] > zthr]
        q = voxel_down(q, a.voxel).astype(np.float32)
        out[f"points_{j}"] = q
        nraw.append(len(p)); nfin.append(len(q))
    (np.savez_compressed if a.compress else np.savez)(a.dst, **out)
    import os
    sz = os.path.getsize(a.dst) / 1e6
    print(f"  kept frames: {len(kept)}; in-range pts/frame median {int(np.median(nraw))}; "
          f"after ground-drop+voxel {a.voxel} m: median {int(np.median(nfin))} min {min(nfin)} max {max(nfin)} total {sum(nfin)}")
    print(f"  wrote {a.dst}: {sz:.1f} MB ({'compressed' if a.compress else 'uncompressed'} npz)")
    if sz > 60:
        print("  WARNING: > 60 MB target; rerun with --voxel 0.08 or --compress", file=sys.stderr)


if __name__ == "__main__":
    main()
