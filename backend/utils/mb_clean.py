"""
MusicBrainz CSV Cleaner
Resolves parent/child work duplicates by:
  1. Identifying child works (title contains ': ')
  2. Grouping them by parent title
  3. For each movement, picking the row with the most recordings (count_with_length)
  4. Summing the chosen stat across movements to get a total duration per parent work
  5. Writing a cleaned CSV with one row per parent work

Usage:
    python clean_works.py beethoven.csv
    python clean_works.py beethoven.csv --stat median --out beethoven_clean.csv
"""

import csv
import argparse
from pathlib import Path
from collections import defaultdict


STAT_COLUMN = "average"   # overridden by --stat


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


def format_duration(ms: int) -> str:
    """Format milliseconds as H:MM:SS or M:SS."""
    seconds = ms // 1000
    minutes, secs = divmod(seconds, 60)
    hours, mins = divmod(minutes, 60)
    return f"{hours}:{mins:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def parent_title(title: str) -> str:
    """Extract parent title from a child work title (everything before ': ')."""
    return title.split(": ", 1)[0]


def is_child(title: str) -> bool:
    return ": " in title


def load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def clean(rows: list[dict], stat: str) -> list[dict]:
    """
    Main cleaning logic. Returns one cleaned row per parent work.
    """
    # Separate children and parents
    children = [r for r in rows if is_child(r["work"])]
    parents  = {r["work"]: r for r in rows if not is_child(r["work"])}

    # Group children by their parent title, then by movement name
    # Structure: parent_title -> movement_title -> [row, row, ...]
    by_parent: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in children:
        by_parent[parent_title(row["work"])][row["work"]].append(row)

    # Also collect parent titles that only appear as children (no explicit parent row)
    all_parent_titles = set(by_parent.keys()) | set(parents.keys())

    results = []
    orphan_parents = []  # parents with no children at all

    for ptitle in sorted(all_parent_titles):
        movements = by_parent.get(ptitle, {})

        if not movements:
            # Pure parent, no child movements found — keep original row as-is
            if ptitle in parents:
                orphan_parents.append(parents[ptitle])
            continue

        # For each movement, pick the row with the highest count_with_length
        chosen_rows = []
        for movement_title, candidates in movements.items():
            def count_key(r):
                try:
                    return int(r.get("count_with_length") or 0)
                except ValueError:
                    return 0
            best = max(candidates, key=count_key)
            chosen_rows.append(best)

        # Sum the chosen stat across movements
        total_ms = 0
        missing = []
        for row in chosen_rows:
            ms = parse_duration(row.get(stat, ""))
            if ms is not None:
                total_ms += ms
            else:
                missing.append(row["work"])

        if missing:
            print(f"  ⚠  '{ptitle}': no '{stat}' data for {len(missing)} movement(s), skipping them:")
            for m in missing:
                print(f"       – {m}")

        total_count_with_length = sum(
            int(r.get("count_with_length") or 0) for r in chosen_rows
        )
        total_count_total = sum(
            int(r.get("count_total") or 0) for r in chosen_rows
        )
        num_movements = len(chosen_rows)

        results.append({
            "work":                ptitle,
            "num_movements":       num_movements,
            "duration":            format_duration(total_ms) if total_ms else "",
            "duration_ms":         total_ms or "",
            "stat_used":           stat,
            "count_with_length":   total_count_with_length,
            "count_total":         total_count_total,
        })

    if orphan_parents:
        print(f"\n  ℹ  {len(orphan_parents)} works had no child movements and are passed through unchanged:")
        for r in orphan_parents:
            print(f"       – {r['work']}")

    results.sort(key=lambda r: r.get("duration_ms") or 0, reverse=True)
    return results, orphan_parents


def write_csv(results: list[dict], orphans: list[dict], stat: str, path: Path) -> None:
    fields = ["work", "num_movements", "duration", "duration_ms",
              "stat_used", "count_with_length", "count_total"]

    # Convert orphan rows to the same schema for appending
    orphan_converted = []
    for r in orphans:
        ms = parse_duration(r.get(stat, ""))
        orphan_converted.append({
            "work":              r["work"],
            "num_movements":     "",
            "duration":          r.get(stat, ""),
            "duration_ms":       ms or "",
            "stat_used":         stat,
            "count_with_length": r.get("count_with_length", ""),
            "count_total":       r.get("count_total", ""),
        })

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
        if orphan_converted:
            writer.writerows(orphan_converted)

    print(f"\n  💾 Saved → {path}")
    print(f"     {len(results)} works rebuilt from movements")
    if orphan_converted:
        print(f"     {len(orphan_converted)} works passed through (no movements found)")


def main():
    parser = argparse.ArgumentParser(
        description="Clean a MusicBrainz works CSV by summing child movement durations."
    )
    parser.add_argument("input", help="Input CSV file (output of musicbrainz_client.py)")
    parser.add_argument(
        "--stat", choices=["average", "median", "min", "max"], default="average",
        help="Which duration column to sum across movements (default: average)"
    )
    parser.add_argument(
        "--out", default=None, metavar="FILE",
        help="Output CSV path (default: <input_stem>_clean.csv)"
    )
    args = parser.parse_args()

    input_path  = Path(args.input)
    output_path = Path(args.out) if args.out else input_path.with_stem(input_path.stem + "_clean")

    print(f"\n{'='*60}")
    print(f"  MusicBrainz CSV Cleaner")
    print(f"{'='*60}")
    print(f"  Input  : {input_path}")
    print(f"  Stat   : {args.stat}")
    print(f"  Output : {output_path}")
    print(f"{'='*60}\n")

    rows = load_csv(input_path)
    print(f"  Loaded {len(rows)} rows\n")

    results, orphans = clean(rows, args.stat)
    write_csv(results, orphans, args.stat, output_path)

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()