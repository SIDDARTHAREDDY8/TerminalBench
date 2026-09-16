#!/usr/bin/env python3
"""Stream the whole bag once (read-only) and report per-topic message counts,
raw payload bytes, rates and time spans.  Also estimates the trimmed bag size
for a topic subset using the bag's overall zstd ratio (payload -> on-disk)."""
import argparse, sys, time
from mcap.reader import make_reader

SPEC_TOPICS = ["/hesai/points", "/livox/lidar", "/fused_points",
               "/fixposition/odometry_enu", "/fixposition/odometry_llh",
               "/fixposition/poiimu", "/fixposition/fpa/corrimu",
               "/odometry/wheels", "/tf", "/tf_static"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--subset", nargs="*", default=SPEC_TOPICS)
    a = ap.parse_args()
    t0 = time.time()
    with open(a.src, "rb") as f:
        r = make_reader(f)
        s = r.get_summary()
        comp = sum(c.chunk_length for c in s.chunk_indexes)
        uncomp = sum(c.uncompressed_size for c in s.chunk_indexes)
        cnt, nb, tmin, tmax = {}, {}, {}, {}
        n = 0
        for schema, ch, m in r.iter_messages(log_time_order=False):
            tp = ch.topic
            cnt[tp] = cnt.get(tp, 0) + 1
            nb[tp] = nb.get(tp, 0) + len(m.data)
            tmin[tp] = min(tmin.get(tp, m.log_time), m.log_time)
            tmax[tp] = max(tmax.get(tp, m.log_time), m.log_time)
            n += 1
            if n % 20000 == 0:
                print(f"  ... {n} msgs, {time.time()-t0:.0f}s", file=sys.stderr)
    ratio = comp / uncomp
    print(f"streamed {n} messages in {time.time()-t0:.1f}s; chunk bytes on disk {comp/1e9:.3f} GB, "
          f"uncompressed {uncomp/1e9:.3f} GB, zstd ratio {ratio:.3f}")
    print()
    print(f"| {'topic':30s} | {'msgs':>6s} | {'payload MB':>10s} | {'est. zstd MB':>12s} | {'rate Hz':>7s} | {'span s':>7s} |")
    print(f"|{'-'*32}|{'-'*8}|{'-'*12}|{'-'*14}|{'-'*9}|{'-'*9}|")
    tot = 0
    for tp in sorted(nb, key=lambda k: -nb[k]):
        span = (tmax[tp] - tmin[tp]) / 1e9
        rate = (cnt[tp] - 1) / span if span > 0 else 0
        print(f"| {tp:30s} | {cnt[tp]:6d} | {nb[tp]/1e6:10.1f} | {nb[tp]*ratio/1e6:12.1f} | {rate:7.2f} | {span:7.1f} |")
        tot += nb[tp]
    print(f"| {'TOTAL':30s} | {n:6d} | {tot/1e6:10.1f} | {tot*ratio/1e6:12.1f} | | |")
    sub = sum(nb.get(t, 0) for t in a.subset)
    print()
    print(f"subset {a.subset}")
    print(f"  payload {sub/1e6:.1f} MB ({100*sub/tot:.1f}% of all payload); est. on-disk zstd {sub*ratio/1e6:.1f} MB "
          f"(assumes bag-wide ratio; point clouds compress a bit worse than images)")

if __name__ == "__main__":
    main()
