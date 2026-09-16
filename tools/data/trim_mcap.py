#!/usr/bin/env python3
"""Trim a ROS 2 mcap bag to a subset of topics (and optionally a time window).

Copies schemas, channels (incl. metadata such as offered_qos_profiles), messages,
metadata records and attachments to a new mcap written with zstd chunk
compression.  Log and publish times are preserved verbatim.

Usage:
  trim_mcap.py --in SRC.mcap --out DST.mcap --topics /a /b ... \
               [--start-sec S] [--duration-sec D] [--chunk-size BYTES]

--start-sec is relative to the first message in the bag (seconds).
Streaming: the source is never loaded into memory (chunk-by-chunk read).
"""
import argparse
import sys
import time

from mcap.reader import make_reader
from mcap.writer import Writer, CompressionType


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    ap.add_argument("--topics", nargs="+", required=True)
    ap.add_argument("--start-sec", type=float, default=None, help="offset from first message (s)")
    ap.add_argument("--duration-sec", type=float, default=None)
    ap.add_argument("--chunk-size", type=int, default=4 * 1024 * 1024)
    ap.add_argument("--no-attachments", action="store_true")
    args = ap.parse_args()

    want = set(args.topics)
    t0 = time.time()
    with open(args.src, "rb") as fin, open(args.dst, "wb") as fout:
        reader = make_reader(fin)
        summary = reader.get_summary()
        hdr = reader.get_header()
        stats = summary.statistics
        bag_start = stats.message_start_time
        start_ns = None if args.start_sec is None else bag_start + int(args.start_sec * 1e9)
        end_ns = None
        if args.duration_sec is not None:
            base = start_ns if start_ns is not None else bag_start
            end_ns = base + int(args.duration_sec * 1e9)

        present = {ch.topic for ch in summary.channels.values()}
        missing = want - present
        if missing:
            print(f"WARNING: topics not in source: {sorted(missing)}", file=sys.stderr)

        writer = Writer(fout, chunk_size=args.chunk_size, compression=CompressionType.ZSTD)
        writer.start(profile=hdr.profile or "ros2", library="trim_mcap.py (python mcap)")

        # copy rosbag2 metadata records (e.g. {"ROS_DISTRO": ...})
        for md in reader.iter_metadata():
            writer.add_metadata(md.name, md.metadata)
        if not args.no_attachments:
            for att in reader.iter_attachments():
                writer.add_attachment(att.create_time, att.log_time, att.name, att.media_type, att.data)

        schema_map = {}   # src schema id -> dst id
        channel_map = {}  # src channel id -> dst id
        counts = {}
        nbytes = {}
        first_ts = None
        last_ts = None
        for schema, channel, msg in reader.iter_messages(
            topics=sorted(want), start_time=start_ns, end_time=end_ns, log_time_order=True
        ):
            if channel.id not in channel_map:
                if schema is not None and schema.id not in schema_map:
                    schema_map[schema.id] = writer.register_schema(schema.name, schema.encoding, schema.data)
                sid = schema_map[schema.id] if schema is not None else 0
                channel_map[channel.id] = writer.register_channel(
                    channel.topic, channel.message_encoding, sid, dict(channel.metadata)
                )
            writer.add_message(
                channel_map[channel.id],
                log_time=msg.log_time,
                data=msg.data,
                publish_time=msg.publish_time,
                sequence=msg.sequence,
            )
            counts[channel.topic] = counts.get(channel.topic, 0) + 1
            nbytes[channel.topic] = nbytes.get(channel.topic, 0) + len(msg.data)
            first_ts = msg.log_time if first_ts is None else min(first_ts, msg.log_time)
            last_ts = msg.log_time if last_ts is None else max(last_ts, msg.log_time)
        writer.finish()

    total = sum(counts.values())
    print(f"wrote {args.dst}: {total} messages in {time.time()-t0:.1f}s")
    if first_ts is not None:
        print(f"  log-time span: {first_ts} .. {last_ts} ({(last_ts-first_ts)/1e9:.3f} s)")
    for tp in sorted(counts):
        print(f"  {tp:32s} {counts[tp]:8d} msgs {nbytes[tp]/1e6:10.2f} MB (raw payload)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
