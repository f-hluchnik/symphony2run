"""
MusicBrainz API Client
Fetches recording lengths (average/min/max) for works by an artist.

Usage:
    # All works for an artist (sorted by average duration):
    python musicbrainz_client.py --artist "Beethoven"

    # Specific work only:
    python musicbrainz_client.py --artist "Beethoven" --work "Symphony No. 5 in C minor, Op. 67"

    # Change statistic and output format:
    python musicbrainz_client.py --artist "Queen" --stat median --output csv
"""

import csv
import sys
import time
import argparse
import statistics
import requests

BASE_URL = "https://musicbrainz.org/ws/2"
HEADERS = {
    "User-Agent": "MusicBrainzDemoClient/1.0 (example@example.com)",
    "Accept": "application/json",
}

# MusicBrainz rate limit: max 1 request/second
RATE_LIMIT_DELAY = 1.1

# Use a persistent session with automatic retries on connection errors
_session = requests.Session()
_adapter = requests.adapters.HTTPAdapter(
    max_retries=requests.adapters.Retry(
        total=5,
        backoff_factor=2,          # waits 2, 4, 8, 16s between retries
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
)
_session.mount("https://", _adapter)
_session.headers.update(HEADERS)

# Use certifi's CA bundle if available (fixes macOS SSL issues)
try:
    import certifi
    _SSL_VERIFY = certifi.where()
except ImportError:
    _SSL_VERIFY = True


def api_get(endpoint: str, params: dict) -> dict:
    """Make a rate-limited GET request to the MusicBrainz API."""
    params["fmt"] = "json"
    url = f"{BASE_URL}/{endpoint}"
    resp = _session.get(url, params=params, timeout=15, verify=_SSL_VERIFY)
    resp.raise_for_status()
    time.sleep(RATE_LIMIT_DELAY)
    return resp.json()


def search_artist(artist_name: str) -> tuple[str, str]:
    """Search for an artist and return (mbid, resolved_name)."""
    print(f"🔍 Searching for artist: {artist_name!r}", file=sys.stderr)
    data = api_get("artist", {"query": artist_name, "limit": 5})
    artists = data.get("artists", [])
    if not artists:
        raise ValueError(f"No artist found for: {artist_name!r}")
    best = artists[0]
    print(f"   ✓ Found: {best['name']} (MBID: {best['id']})", file=sys.stderr)
    return best["id"], best["name"]


def fetch_all_works(artist_mbid: str) -> list[dict]:
    """Fetch every work linked to an artist, handling pagination."""
    print(f"📚 Fetching all works for artist...", file=sys.stderr)
    offset = 0
    limit = 10
    all_works = []

    i = 2
    while True:
        data = api_get("work", {
            "artist": artist_mbid,
            "limit": limit,
            "offset": offset,
        })
        works = data.get("works", [])
        total = data.get("work-count", 0)
        all_works.extend(works)
        offset += len(works)
        print(f"   Fetched {offset}/{total} works...", file=sys.stderr)
        if offset >= total or not works or i > 1:
            break
        i += 1

    print(f"   ✓ Total works: {len(all_works)}", file=sys.stderr)
    return all_works


def find_best_work(works: list[dict], work_name: str) -> dict:
    """Return the work from the list that best matches work_name."""
    work_name_lower = work_name.lower()
    best_match = None
    best_score = -1
    for work in works:
        name = work.get("title", "")
        score = _match_score(work_name_lower, name.lower())
        if score > best_score:
            best_score = score
            best_match = work
    if not best_match:
        raise ValueError("No works available to match against.")
    print(f"   ✓ Best match: {best_match['title']!r} (score={best_score:.2f})", file=sys.stderr)
    return best_match


def _match_score(query: str, candidate: str) -> float:
    """Simple substring + token overlap scoring."""
    if query == candidate:
        return 1.0
    if query in candidate or candidate in query:
        return 0.9
    q_tokens = set(query.split())
    c_tokens = set(candidate.split())
    overlap = q_tokens & c_tokens
    if not q_tokens:
        return 0.0
    return len(overlap) / len(q_tokens)


def fetch_recordings_for_work(work_mbid: str) -> list[dict]:
    """Browse all recordings linked to a work."""
    offset = 0
    limit = 100
    all_recordings = []

    while True:
        data = api_get("recording", {
            "work": work_mbid,
            "limit": limit,
            "offset": offset,
        })
        recordings = data.get("recordings", [])
        total = data.get("recording-count", 0)
        all_recordings.extend(recordings)
        offset += len(recordings)
        if offset >= total or not recordings:
            break

    return all_recordings


def compute_stats(recordings: list[dict]) -> dict | None:
    """Compute length statistics from a list of recordings. Returns None if no data."""
    lengths = [r["length"] for r in recordings if r.get("length")]
    if not lengths:
        return None
    avg = statistics.mean(lengths)
    median = statistics.median(lengths)
    return {
        "count_with_length": len(lengths),
        "count_total": len(recordings),
        "average_ms": int(avg),
        "median_ms": int(median),
        "min_ms": min(lengths),
        "max_ms": max(lengths),
        "average": format_duration(int(avg)),
        "median": format_duration(int(median)),
        "min": format_duration(min(lengths)),
        "max": format_duration(max(lengths)),
    }


def format_duration(ms: int) -> str:
    """Format milliseconds as H:MM:SS or M:SS."""
    seconds = ms // 1000
    minutes, secs = divmod(seconds, 60)
    hours, mins = divmod(minutes, 60)
    if hours:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


# ---------------------------------------------------------------------------
# High-level entry points
# ---------------------------------------------------------------------------

def get_all_works_with_durations(artist_name: str, stat: str = "average") -> list[dict]:
    """
    Fetch all works for an artist and compute duration stats for each.
    Returns a list of dicts sorted by the chosen stat descending.
    Works with no recording length data are included at the end.
    """
    artist_mbid, resolved_artist = search_artist(artist_name)
    works = fetch_all_works(artist_mbid)

    results = []
    total = len(works)
    for i, work in enumerate(works, 1):
        title = work.get("title", "(unknown)")
        mbid = work["id"]
        print(f"   [{i}/{total}] {title}", file=sys.stderr)
        recordings = fetch_recordings_for_work(mbid)
        stats = compute_stats(recordings)
        entry = {
            "artist": resolved_artist,
            "work": title,
            "work_mbid": mbid,
        }
        if stats:
            entry.update(stats)
            entry["chosen_duration"] = stats[stat]
            entry["chosen_duration_ms"] = stats[f"{stat}_ms"]
        else:
            entry["chosen_duration"] = None
            entry["chosen_duration_ms"] = None
        results.append(entry)

    # Sort: works with data first by chosen stat descending, unknowns at end
    results.sort(
        key=lambda r: r["chosen_duration_ms"] if r["chosen_duration_ms"] is not None else -1,
        reverse=True,
    )
    return results


def get_single_work_duration(work_name: str, artist_name: str, stat: str = "average") -> dict:
    """Fetch duration stats for a single named work."""
    artist_mbid, resolved_artist = search_artist(artist_name)
    works = fetch_all_works(artist_mbid)
    work = find_best_work(works, work_name)
    recordings = fetch_recordings_for_work(work["id"])

    if not recordings:
        return {"error": "No recordings found for this work."}

    stats = compute_stats(recordings)
    if not stats:
        return {"error": "No recordings with length data found."}

    return {
        "artist": resolved_artist,
        "work": work["title"],
        "stat": stat,
        "duration": stats[stat],
        "duration_ms": stats[f"{stat}_ms"],
        **stats,
    }


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def print_table(results: list[dict], stat: str) -> None:
    col_work = max((len(r["work"]) for r in results), default=4)
    col_work = max(col_work, 4)
    stat_label = stat.capitalize()

    header = (
        f"  {'Work':<{col_work}}  {stat_label:>8}  "
        f"{'Avg':>8}  {'Median':>8}  {'Min':>8}  {'Max':>8}  {'Recordings':>10}"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))

    for r in results:
        dur    = r.get("chosen_duration") or "—"
        avg    = r.get("average") or "—"
        med    = r.get("median") or "—"
        mn     = r.get("min") or "—"
        mx     = r.get("max") or "—"
        cnt    = f"{r.get('count_with_length', 0)}/{r.get('count_total', 0)}"
        print(
            f"  {r['work']:<{col_work}}  {dur:>8}  "
            f"{avg:>8}  {med:>8}  {mn:>8}  {mx:>8}  {cnt:>10}"
        )


def print_csv(results: list[dict], stat: str) -> None:
    fields = ["work", "work_mbid", "chosen_duration", "average", "median",
              "min", "max", "count_with_length", "count_total"]
    writer = csv.DictWriter(sys.stdout, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for r in results:
        writer.writerow({f: r.get(f, "") for f in fields})


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fetch recording lengths for works from MusicBrainz."
    )
    parser.add_argument(
        "--artist", required=True,
        help='Artist/composer name, e.g. "Beethoven"'
    )
    parser.add_argument(
        "--work", default=None,
        help="(Optional) Work name. If omitted, all works are processed."
    )
    parser.add_argument(
        "--stat", choices=["average", "median", "min", "max"], default="average",
        help="Statistic to highlight (default: average)"
    )
    parser.add_argument(
        "--output", choices=["table", "csv"], default="table",
        help="Output format (default: table)"
    )
    args = parser.parse_args()

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"  MusicBrainz Recording Length Lookup", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    print(f"  Artist : {args.artist}", file=sys.stderr)
    if args.work:
        print(f"  Work   : {args.work}", file=sys.stderr)
    else:
        print(f"  Mode   : All works", file=sys.stderr)
    print(f"  Stat   : {args.stat}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

    # ── Single work mode ─────────────────────────────────────────────────────
    if args.work:
        result = get_single_work_duration(args.work, args.artist, args.stat)
        print(f"\n{'='*60}")
        if "error" in result:
            print(f"  ❌ Error: {result['error']}")
        else:
            print(f"  ✅ Result")
            print(f"{'='*60}")
            print(f"  Artist  : {result['artist']}")
            print(f"  Work    : {result['work']}")
            print(f"  Stat    : {result['stat'].capitalize()}")
            print(f"  Duration: {result['duration']}")
            print()
            print(f"  All stats ({result['count_with_length']}/{result['count_total']} recordings have length):")
            print(f"    Average : {result['average']}")
            print(f"    Median  : {result['median']}")
            print(f"    Min     : {result['min']}")
            print(f"    Max     : {result['max']}")
        print(f"{'='*60}\n")

    # ── All-works mode ────────────────────────────────────────────────────────
    else:
        results = get_all_works_with_durations(args.artist, args.stat)

        print(f"\n{'='*60}", file=sys.stderr)
        print(f"  ✅ Done — {len(results)} works processed", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)

        if not results:
            print("No works found.")
            return

        if args.output == "csv":
            print_csv(results, args.stat)
        else:
            artist = results[0]["artist"]
            print(f"\n  Artist : {artist}")
            print(f"  Sorted by {args.stat} duration (longest first)\n")
            print_table(results, args.stat)
            print()


if __name__ == "__main__":
    main()