"""Step 1 of adding a composer: download recording lengths from MusicBrainz.

For every work MusicBrainz links to the composer, fetch all its recordings and
write length statistics to data/raw/<surname>.csv. MusicBrainz lists movements
as works of their own ("Symphony No. 5: I. Allegro con brio"); step 2,
clean_works.py, adds them up into whole works.

    python -m pipeline.fetch_musicbrainz "Antonín Dvořák"

    # Look at a single work without writing anything:
    python -m pipeline.fetch_musicbrainz "Antonín Dvořák" --work "Symphony no. 9"

Run from the backend/ directory. It takes a while: MusicBrainz allows one
request per second, and a prolific composer has thousands of works (Mozart:
about an hour). Requests are made one at a time; threads would not help.
"""

import argparse
import csv
import statistics
import sys
import time
import unicodedata
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter, Retry

from pipeline.durations import format_duration

API_URL = "https://musicbrainz.org/ws/2"
# MusicBrainz asks every client to identify itself with a way to reach its author.
USER_AGENT = "Symphony2Run/1.0 (https://github.com/f-hluchnik/symphony2run)"
RAW_DIR = Path("data/raw")
STATS = ("average", "median", "min", "max")
FIELDS = ["composer", "work", "work_mbid", "count_total", "count_with_length"] + [
    f"{stat}_ms" for stat in STATS
]


class MusicBrainz:
    """A small MusicBrainz API client: rate-limited, with retries on transient errors."""

    MIN_INTERVAL = 1.1  # seconds between requests; the limit is 1 per second

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
        self._session.mount("https://", HTTPAdapter(max_retries=retries))
        self._last_request = 0.0

    def get(self, endpoint: str, **params) -> dict:
        time.sleep(max(0.0, self.MIN_INTERVAL - (time.monotonic() - self._last_request)))
        try:
            response = self._session.get(
                f"{API_URL}/{endpoint}", params={**params, "fmt": "json"}, timeout=15
            )
        finally:
            self._last_request = time.monotonic()
        response.raise_for_status()
        return response.json()

    def browse(self, entity: str, **params) -> list[dict]:
        """Every item of a paginated list, e.g. browse("work", artist=mbid)."""
        items: list[dict] = []
        while True:
            page = self.get(entity, **params, limit=100, offset=len(items))
            batch = page.get(f"{entity}s", [])
            items += batch
            if not batch or len(items) >= page.get(f"{entity}-count", 0):
                return items

    def find_artist(self, name: str) -> tuple[str, str]:
        """(MBID, canonical name) of the best match for `name`."""
        artists = self.get("artist", query=name, limit=1).get("artists", [])
        if not artists:
            raise SystemExit(f"No artist found for {name!r}.")
        return artists[0]["id"], artists[0]["name"]


def length_stats(recordings: list[dict]) -> dict:
    """Counts, plus length statistics in ms if any recording has a length."""
    lengths = [r["length"] for r in recordings if r.get("length")]
    stats = {"count_total": len(recordings), "count_with_length": len(lengths)}
    if lengths:
        stats |= {
            "average_ms": round(statistics.mean(lengths)),
            "median_ms": round(statistics.median(lengths)),
            "min_ms": min(lengths),
            "max_ms": max(lengths),
        }
    return stats


def fetch_composer(mb: MusicBrainz, composer_id: str, composer: str) -> list[dict]:
    works = mb.browse("work", artist=composer_id)
    log(f"{len(works)} works. Fetching their recordings...")
    rows = []
    for done, work in enumerate(works, start=1):
        try:
            recordings = mb.browse("recording", work=work["id"])
        except requests.RequestException as error:
            log(f"  skipped {work['title']!r}: {error}")
            continue
        rows.append(
            {"composer": composer, "work": work["title"], "work_mbid": work["id"]}
            | length_stats(recordings)
        )
        if done % 50 == 0:
            log(f"  {done}/{len(works)}")
    return sorted(rows, key=lambda row: row["work"])


def show_work(mb: MusicBrainz, composer_id: str, composer: str, title: str) -> None:
    """Print the statistics of the composer's work whose title best matches `title`."""
    matches = [
        w for w in mb.browse("work", artist=composer_id) if title.lower() in w["title"].lower()
    ]
    if not matches:
        raise SystemExit(f"No work of {composer} has {title!r} in its title.")
    work = min(matches, key=lambda w: len(w["title"]))  # the whole work rather than a movement
    stats = length_stats(mb.browse("recording", work=work["id"]))
    print(f"{composer}: {work['title']}")
    print(f"  {stats['count_with_length']} of {stats['count_total']} recordings have a length")
    for stat in STATS:
        if f"{stat}_ms" in stats:
            print(f"  {stat:<8} {format_duration(stats[f'{stat}_ms'])}")


def surname_slug(name: str) -> str:
    """'Antonín Dvořák' -> 'dvorak', for file names."""
    surname = unicodedata.normalize("NFKD", name.split()[-1].lower())
    return surname.encode("ascii", "ignore").decode()


def log(message: str) -> None:
    print(message, file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download recording lengths from MusicBrainz.")
    parser.add_argument("composer", help='as MusicBrainz knows them, e.g. "Antonín Dvořák"')
    parser.add_argument("--work", help="only print the statistics of this one work")
    parser.add_argument("--out", type=Path, help="CSV to write (default: data/raw/<surname>.csv)")
    args = parser.parse_args()

    mb = MusicBrainz()
    composer_id, composer = mb.find_artist(args.composer)
    log(f"Composer: {composer} ({composer_id})")
    if args.work:
        show_work(mb, composer_id, composer, args.work)
        return

    rows = fetch_composer(mb, composer_id, composer)
    out = args.out or RAW_DIR / f"{surname_slug(composer)}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    log(f"Saved {len(rows)} works to {out}.\nNext: python -m pipeline.clean_works {out}")


if __name__ == "__main__":
    main()
