"""
MusicBrainz API Client
Fetches recording lengths (average/min/max) for works by an artist.

Usage:
    # All works — saves to beethoven.csv / beethoven_table.txt automatically:
    python musicbrainz_client.py --artist "Beethoven"

    # Specific work only (prints to terminal):
    python musicbrainz_client.py --artist "Beethoven" --work "Symphony No. 5 in C minor, Op. 67"

    # Choose stat and parallelism:
    python musicbrainz_client.py --artist "Queen" --stat median --workers 5

    # Override output directory:
    python musicbrainz_client.py --artist "Bach" --outdir ./data
"""

import csv
import re
import sys
import time
import threading
import argparse
import statistics
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

BASE_URL = "https://musicbrainz.org/ws/2"
HEADERS = {
    "User-Agent": "MusicBrainzDemoClient/1.0 (example@example.com)",
    "Accept": "application/json",
}

# MusicBrainz rate limit: 1 request/second across ALL threads
RATE_LIMIT_DELAY = 1.1
_rate_lock = threading.Lock()
_last_request_time: float = 0.0

# Use a persistent session with automatic retries on connection errors
_session = requests.Session()
_adapter = requests.adapters.HTTPAdapter(
    max_retries=requests.adapters.Retry(
        total=5,
        backoff_factor=2,
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


# ---------------------------------------------------------------------------
# Core API helper
# ---------------------------------------------------------------------------

def api_get(endpoint: str, params: dict) -> dict:
    """
    Rate-limited GET request. A global lock ensures we never exceed
    1 request/second even when called from multiple threads.
    """
    global _last_request_time
    params["fmt"] = "json"
    url = f"{BASE_URL}/{endpoint}"

    with _rate_lock:
        now = time.monotonic()
        wait = RATE_LIMIT_DELAY - (now - _last_request_time)
        if wait > 0:
            time.sleep(wait)
        resp = _session.get(url, params=params, timeout=15, verify=_SSL_VERIFY)
        _last_request_time = time.monotonic()

    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Artist / work helpers
# ---------------------------------------------------------------------------

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
    print("📚 Fetching all works for artist...", file=sys.stderr)
    offset, limit, all_works = 0, 100, []
    while True:
        data = api_get("work", {"artist": artist_mbid, "limit": limit, "offset": offset})
        works = data.get("works", [])
        total = data.get("work-count", 0)
        all_works.extend(works)
        offset += len(works)
        print(f"   Fetched {offset}/{total} works...", file=sys.stderr)
        if offset >= total or not works:
            break
    print(f"   ✓ Total works: {len(all_works)}", file=sys.stderr)
    return all_works


def find_best_work(works: list[dict], work_name: str) -> dict:
    """Return the work from the list that best matches work_name."""
    work_name_lower = work_name.lower()
    best_match = max(works, key=lambda w: _match_score(work_name_lower, w.get("title", "").lower()))
    score = _match_score(work_name_lower, best_match.get("title", "").lower())
    print(f"   ✓ Best match: {best_match['title']!r} (score={score:.2f})", file=sys.stderr)
    return best_match


def _match_score(query: str, candidate: str) -> float:
    if query == candidate:
        return 1.0
    if query in candidate or candidate in query:
        return 0.9
    q_tokens = set(query.split())
    c_tokens = set(candidate.split())
    overlap = q_tokens & c_tokens
    return len(overlap) / len(q_tokens) if q_tokens else 0.0


# ---------------------------------------------------------------------------
# Recording fetcher
# ---------------------------------------------------------------------------

def fetch_recordings_for_work(work_mbid: str) -> list[dict]:
    """Fetch all recordings linked to a work (paginated)."""
    offset, limit, all_recordings = 0, 100, []
    while True:
        data = api_get("recording", {"work": work_mbid, "limit": limit, "offset": offset})
        recordings = data.get("recordings", [])
        total = data.get("recording-count", 0)
        all_recordings.extend(recordings)
        offset += len(recordings)
        if offset >= total or not recordings:
            break
    return all_recordings


# ---------------------------------------------------------------------------
# Stats / formatting
# ---------------------------------------------------------------------------

def compute_stats(recordings: list[dict]) -> dict | None:
    lengths = [r["length"] for r in recordings if r.get("length")]
    if not lengths:
        return None
    avg = statistics.mean(lengths)
    med = statistics.median(lengths)
    return {
        "count_with_length": len(lengths),
        "count_total": len(recordings),
        "average_ms": int(avg),
        "median_ms":  int(med),
        "min_ms":     min(lengths),
        "max_ms":     max(lengths),
        "average":    format_duration(int(avg)),
        "median":     format_duration(int(med)),
        "min":        format_duration(min(lengths)),
        "max":        format_duration(max(lengths)),
    }


def format_duration(ms: int) -> str:
    seconds = ms // 1000
    minutes, secs = divmod(seconds, 60)
    hours, mins = divmod(minutes, 60)
    return f"{hours}:{mins:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


# ---------------------------------------------------------------------------
# High-level entry points
# ---------------------------------------------------------------------------

def _process_work(work: dict, stat: str, index: int, total: int) -> dict:
    """Fetch recordings for one work and return a result dict. Thread-safe."""
    title = work.get("title", "(unknown)")
    mbid  = work["id"]
    print(f"   [{index}/{total}] {title}", file=sys.stderr)
    recordings = fetch_recordings_for_work(mbid)
    stats = compute_stats(recordings)
    entry = {"work": title, "work_mbid": mbid}
    if stats:
        entry.update(stats)
        entry["chosen_duration"]    = stats[stat]
        entry["chosen_duration_ms"] = stats[f"{stat}_ms"]
    else:
        entry["chosen_duration"]    = None
        entry["chosen_duration_ms"] = None
    return entry


def get_all_works_with_durations(
    artist_name: str,
    stat: str = "average",
    workers: int = 3,
) -> tuple[str, list[dict]]:
    """
    Fetch all works for an artist and compute duration stats in parallel.
    Returns (resolved_artist_name, sorted_results).
    workers: number of concurrent threads (each still respects the global rate limit).
    """
    artist_mbid, resolved_artist = search_artist(artist_name)
    works = fetch_all_works(artist_mbid)
    total = len(works)

    print(f"🎵 Fetching recordings ({workers} workers)...", file=sys.stderr)

    # Submit all work fetches to the thread pool; order in results is preserved
    # by tagging each future with its original index.
    index_map: dict = {}
    results_map: dict = {}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_process_work, work, stat, i + 1, total): i
            for i, work in enumerate(works)
        }
        for future in as_completed(futures):
            i = futures[future]
            try:
                results_map[i] = future.result()
            except Exception as exc:
                title = works[i].get("title", "?")
                print(f"   ⚠ Error processing {title!r}: {exc}", file=sys.stderr)
                results_map[i] = {
                    "work": title,
                    "work_mbid": works[i]["id"],
                    "chosen_duration": None,
                    "chosen_duration_ms": None,
                }

    results = [results_map[i] for i in range(total) if i in results_map]

    # Attach artist to every entry, then sort
    for r in results:
        r["artist"] = resolved_artist

    results.sort(
        key=lambda r: r["chosen_duration_ms"] if r["chosen_duration_ms"] is not None else -1,
        reverse=True,
    )
    return resolved_artist, results


def get_single_work_duration(work_name: str, artist_name: str, stat: str = "average") -> dict:
    """Fetch duration stats for a single named work."""
    artist_mbid, resolved_artist = search_artist(artist_name)
    works = fetch_all_works(artist_mbid)
    work  = find_best_work(works, work_name)
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
# Output helpers
# ---------------------------------------------------------------------------

def _safe_filename(name: str) -> str:
    """Turn an artist name into a safe filename stem."""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s]+", "_", name)
    return name


def write_csv(results: list[dict], path: Path) -> None:
    fields = ["work", "work_mbid", "chosen_duration", "average", "median",
              "min", "max", "count_with_length", "count_total"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow({field: r.get(field, "") for field in fields})
    print(f"   💾 CSV saved  → {path}", file=sys.stderr)


def write_table(results: list[dict], stat: str, artist: str, path: Path) -> None:
    lines = []
    col_work = max((len(r["work"]) for r in results), default=4)
    stat_label = stat.capitalize()
    header = (
        f"  {'Work':<{col_work}}  {stat_label:>8}  "
        f"{'Avg':>8}  {'Median':>8}  {'Min':>8}  {'Max':>8}  {'Recordings':>10}"
    )
    lines.append(f"  Artist : {artist}")
    lines.append(f"  Sorted by {stat} duration (longest first)\n")
    lines.append(header)
    lines.append("  " + "-" * (len(header) - 2))

    for r in results:
        dur = r.get("chosen_duration") or "—"
        avg = r.get("average") or "—"
        med = r.get("median") or "—"
        mn  = r.get("min") or "—"
        mx  = r.get("max") or "—"
        cnt = f"{r.get('count_with_length', 0)}/{r.get('count_total', 0)}"
        lines.append(
            f"  {r['work']:<{col_work}}  {dur:>8}  "
            f"{avg:>8}  {med:>8}  {mn:>8}  {mx:>8}  {cnt:>10}"
        )

    table_str = "\n".join(lines)
    print(table_str)  # also print to stdout
    with path.open("w", encoding="utf-8") as f:
        f.write(table_str + "\n")
    print(f"   💾 Table saved → {path}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fetch recording lengths for works from MusicBrainz."
    )
    parser.add_argument("--artist", required=True, help='Artist/composer name, e.g. "Beethoven"')
    parser.add_argument("--work",   default=None,  help="(Optional) specific work name")
    parser.add_argument(
        "--stat", choices=["average", "median", "min", "max"], default="average",
        help="Statistic to highlight (default: average)",
    )
    parser.add_argument(
        "--workers", type=int, default=3, metavar="N",
        help="Parallel workers for recording lookups (default: 3, max recommended: 5)",
    )
    parser.add_argument(
        "--outdir", default=".", metavar="DIR",
        help="Directory to save output files (default: current directory)",
    )
    args = parser.parse_args()

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"  MusicBrainz Recording Length Lookup", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    print(f"  Artist  : {args.artist}", file=sys.stderr)
    if args.work:
        print(f"  Work    : {args.work}", file=sys.stderr)
    else:
        print(f"  Mode    : All works", file=sys.stderr)
        print(f"  Workers : {args.workers}", file=sys.stderr)
    print(f"  Stat    : {args.stat}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # ── Single work mode ──────────────────────────────────────────────────────
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
        artist, results = get_all_works_with_durations(
            args.artist, stat=args.stat, workers=args.workers
        )

        print(f"\n{'='*60}", file=sys.stderr)
        print(f"  ✅ Done — {len(results)} works processed", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)

        if not results:
            print("No works found.")
            return

        stem = _safe_filename(artist)
        write_csv(results, outdir / f"{stem}.csv")
        write_table(results, args.stat, artist, outdir / f"{stem}_table.txt")


if __name__ == "__main__":
    main()