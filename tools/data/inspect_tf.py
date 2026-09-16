#!/usr/bin/env python3
"""List every parent->child TF pair in /tf and /tf_static (streamed, read-only)
and check for the robot sensor-mount frames."""
import argparse, sys, time
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory

WANTED = ["base_link", "hesai", "livox_frame", "livox_front", "livox_rear", "livox_left", "livox_right",
          "vrtk_link", "FP_POI", "FP_ENU0", "FP_ECEF", "odom", "map", "camera_01_link", "camera_02_link"]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--in", dest="src", required=True); a = ap.parse_args()
    t0 = time.time()
    pairs = {}   # (topic, parent, child) -> [count, first_ts, last_ts, sample_xyz_quat]
    frames = set()
    with open(a.src, "rb") as f:
        r = make_reader(f, decoder_factories=[DecoderFactory()])
        for schema, ch, m, msg in r.iter_decoded_messages(topics=["/tf", "/tf_static"]):
            for tr in msg.transforms:
                k = (ch.topic, tr.header.frame_id, tr.child_frame_id)
                st = tr.header.stamp.sec + tr.header.stamp.nanosec * 1e-9
                if k not in pairs:
                    t = tr.transform.translation; q = tr.transform.rotation
                    pairs[k] = [0, st, st, (round(t.x, 4), round(t.y, 4), round(t.z, 4),
                                            round(q.x, 4), round(q.y, 4), round(q.z, 4), round(q.w, 4))]
                p = pairs[k]; p[0] += 1; p[1] = min(p[1], st); p[2] = max(p[2], st)
                frames.add(tr.header.frame_id); frames.add(tr.child_frame_id)
    print(f"scanned /tf + /tf_static in {time.time()-t0:.1f}s")
    print()
    print("| topic | parent | child | n | span s | first (x y z qx qy qz qw) |")
    print("|---|---|---|---|---|---|")
    for (tp, pa, chd), (n, a0, a1, s) in sorted(pairs.items()):
        print(f"| {tp} | {pa} | {chd} | {n} | {a1-a0:.1f} | {' '.join(str(v) for v in s)} |")
    print()
    print("frames present:", sorted(frames))
    print()
    for w in WANTED:
        print(f"  {w:18s} {'PRESENT' if w in frames else 'absent'}")

if __name__ == "__main__":
    main()
