"""Headless CLI helpers for Acteo.

Provide a small command-line tool to scan an input folder and print
detected sequences for quick validation and testing.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional

from .sequence_loader import group_by_timestamp_gap, scan_folder


def run(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="acteo-cli")
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Input folder to scan",
    )
    parser.add_argument(
        "--gap",
        "-g",
        type=int,
        default=10,
        help="Gap seconds for grouping",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output sequences as JSON",
    )
    args = parser.parse_args(argv)

    folder = Path(args.input).expanduser()
    files = scan_folder(str(folder))
    seqs = group_by_timestamp_gap(files, gap_seconds=args.gap)

    if args.json:
        out = []
        for s in seqs:
            out.append({
                "id": s.id,
                "image_count": len(s.image_paths),
                "image_paths": s.image_paths,
                "start_ts": s.start_ts.isoformat(),
                "end_ts": s.end_ts.isoformat(),
            })
        print(json.dumps(out, indent=2))
    else:
        for s in seqs:
            info = (
                "Sequence %s: %d images [%s - %s]"
                % (s.id, len(s.image_paths), s.start_ts, s.end_ts)
            )
            print(info)
            for p in s.image_paths:
                print("  ", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
