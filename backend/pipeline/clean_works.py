"""Step 2 of adding a composer: turn raw MusicBrainz data into whole works.

MusicBrainz lists each movement as a work of its own, named "<work>: <movement>"
("Symphony no. 9 in E minor, op. 95: II. Largo"), and the same movement often
appears several times under different IDs. For each work this script:

  1. takes the movements, i.e. the titles that start with "<work>: ",
  2. for each movement title, keeps the entry with the most timed recordings,
  3. adds up the movements' lengths (median by default) into the work's length.

Works without movements keep their own length. Works shorter than --min (10
minutes by default) or with no length at all are left out: nobody runs to them.

    python -m pipeline.clean_works data/raw/dvorak.csv
    python -m pipeline.clean_works data/raw/dvorak.csv --stat average --min 20:00

Writes data/works/<same name>.csv, the format the app imports at startup.
Read through it before committing: the sums are only as good as MusicBrainz's
titles, so a work with duplicate or oddly named movements can come out too long.
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

from pipeline.durations import format_duration, parse_duration

WORKS_DIR = Path("data/works")
STATS = ("average", "median", "min", "max")
FIELDS = [
    "composer", "work", "num_movements", "duration", "duration_ms",
    "stat_used", "count_with_length", "count_total",
]  # fmt: skip


def as_int(value: str | None) -> int:
    return int(value) if value and value.strip() else 0


def combine(rows: list[dict], stat: str) -> list[dict]:
    """One row per work, movements summed, sorted from longest to shortest."""
    column = f"{stat}_ms"
    movements: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    standalone: dict[str, dict] = {}
    for row in rows:
        parent, separator, _ = row["work"].partition(": ")
        if separator:
            movements[parent][row["work"]].append(row)
        else:
            standalone[row["work"]] = row

    works = []
    for title, entries in movements.items():
        chosen = [
            max(same, key=lambda r: as_int(r["count_with_length"])) for same in entries.values()
        ]
        timed = [r for r in chosen if as_int(r[column])]
        if len(timed) < len(chosen):
            log(f"{title!r}: {len(chosen) - len(timed)} of {len(chosen)} movements have no length")
        works.append(
            work_row(
                chosen[0]["composer"],
                title,
                sum(as_int(r[column]) for r in timed),
                stat,
                num_movements=len(chosen),
                count_with_length=sum(as_int(r["count_with_length"]) for r in chosen),
                count_total=sum(as_int(r["count_total"]) for r in chosen),
            )
        )
    for title, row in standalone.items():
        if title not in movements:
            works.append(
                work_row(
                    row["composer"],
                    title,
                    as_int(row[column]),
                    stat,
                    num_movements=None,
                    count_with_length=as_int(row["count_with_length"]),
                    count_total=as_int(row["count_total"]),
                )
            )
    return sorted(works, key=lambda w: w["duration_ms"], reverse=True)


def work_row(composer: str, title: str, ms: int, stat: str, **counts) -> dict:
    return {
        "composer": composer,
        "work": title,
        "duration": format_duration(ms),
        "duration_ms": ms,
        "stat_used": stat,
        **counts,
    }


def log(message: str) -> None:
    print(message, file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Combine movements into whole works.")
    parser.add_argument("input", type=Path, help="raw CSV from fetch_musicbrainz.py")
    parser.add_argument("--stat", choices=STATS, default="median", help="default: median")
    parser.add_argument("--min", default="10:00", help="shortest work to keep, M:SS or H:MM:SS")
    parser.add_argument("--out", type=Path, help="default: data/works/<input name>.csv")
    args = parser.parse_args()

    min_ms = parse_duration(args.min)
    if min_ms is None:
        parser.error(f"--min must look like 10:00 or 1:00:00, not {args.min!r}")

    with args.input.open(encoding="utf-8") as f:
        works = combine(list(csv.DictReader(f)), args.stat)
    kept = [w for w in works if w["duration_ms"] >= max(min_ms, 1)]

    out = args.out or WORKS_DIR / args.input.name
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(kept)
    log(
        f"Saved {len(kept)} works to {out}; left out {len(works) - len(kept)} "
        f"shorter than {args.min} or without a length."
    )


if __name__ == "__main__":
    main()
