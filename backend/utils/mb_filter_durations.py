"""
Filter a cleaned MusicBrainz CSV to only include works at or above a minimum duration.

Usage:
    python filter_works.py beethoven_clean.csv
    python filter_works.py beethoven_clean.csv --min 20:00
    python filter_works.py beethoven_clean.csv --min 1:00:00 --out long_works.csv
"""

import csv
import argparse
from pathlib import Path


def parse_duration(s: str) -> int | None:
    """Parse M:SS or H:MM:SS into milliseconds. Returns None if blank/invalid."""
    if not s or not s.strip():
        return None
    parts = s.strip().split(":")
    try:
        parts = [int(p) for p in parts]
    except ValueError:
        return None
    if len(parts) == 2:
        return (parts[0] * 60 + parts[1]) * 1000
    if len(parts) == 3:
        return (parts[0] * 3600 + parts[1] * 60 + parts[2]) * 1000
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Filter a MusicBrainz works CSV by minimum duration."
    )
    parser.add_argument("input", help="Input CSV (output of clean_works.py)")
    parser.add_argument(
        "--min", default="10:00", metavar="DURATION",
        help="Minimum duration as M:SS or H:MM:SS (default: 10:00)"
    )
    parser.add_argument(
        "--out", default=None, metavar="FILE",
        help="Output CSV path (default: <input_stem>_filtered.csv)"
    )
    args = parser.parse_args()

    input_path  = Path(args.input)
    output_path = Path(args.out) if args.out else input_path.with_stem(input_path.stem + "_filtered")

    min_ms = parse_duration(args.min)
    if min_ms is None:
        print(f"❌ Could not parse minimum duration: {args.min!r}")
        raise SystemExit(1)

    print(f"\n{'='*60}")
    print(f"  MusicBrainz Works Filter")
    print(f"{'='*60}")
    print(f"  Input      : {input_path}")
    print(f"  Minimum    : {args.min}")
    print(f"  Output     : {output_path}")
    print(f"{'='*60}\n")

    with input_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    kept, skipped, no_data = [], [], []
    for row in rows:
        ms = parse_duration(row.get("duration", ""))
        if ms is None:
            no_data.append(row)
        elif ms >= min_ms:
            kept.append(row)
        else:
            skipped.append(row)

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept)

    print(f"  ✅ Kept    : {len(kept)} works (≥ {args.min})")
    print(f"  ⏭  Skipped : {len(skipped)} works (below threshold)")
    print(f"  ⚠  No data : {len(no_data)} works (no duration, excluded)")
    print(f"\n  💾 Saved → {output_path}")
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()