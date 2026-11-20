import csv
import subprocess
import sys

from pipeline.clean_works import combine
from pipeline.durations import format_duration, parse_duration
from pipeline.fetch_musicbrainz import length_stats, surname_slug


def test_durations_round_trip():
    assert parse_duration("42:10") == (42 * 60 + 10) * 1000
    assert parse_duration("1:02:03") == 3_723_000
    assert format_duration(3_723_000) == "1:02:03"
    assert format_duration(2_530_000) == "42:10"
    for invalid in ("", None, "42", "a:b", "1:2:3:4"):
        assert parse_duration(invalid) is None


def test_length_stats_ignore_recordings_without_length():
    stats = length_stats([{"length": 1000}, {"length": 3000}, {"length": None}, {}])
    assert stats == {
        "count_total": 4,
        "count_with_length": 2,
        "average_ms": 2000,
        "median_ms": 2000,
        "min_ms": 1000,
        "max_ms": 3000,
    }
    assert length_stats([{}]) == {"count_total": 1, "count_with_length": 0}


def test_surname_slug():
    assert surname_slug("Antonín Dvořák") == "dvorak"
    assert surname_slug("Ludwig van Beethoven") == "beethoven"


def raw(work, median_ms, count):
    return {
        "composer": "Antonín Dvořák",
        "work": work,
        "median_ms": str(median_ms) if median_ms else "",
        "count_with_length": str(count),
        "count_total": str(count + 1),
    }


def test_combine_sums_movements_and_keeps_standalone_works():
    rows = [
        raw("Symphony: I. Adagio", 600_000, 5),
        raw("Symphony: I. Adagio", 999_000, 2),  # duplicate with fewer recordings
        raw("Symphony: II. Largo", 700_000, 4),
        raw("Symphony", 1_000_000, 50),  # replaced by the sum of its movements
        raw("Rusalka: Song to the Moon", None, 3),  # no length: counted, not summed
        raw("Rusalka: Act I", 2_000_000, 3),
        raw("Humoresque", 180_000, 9),
    ]
    works = {w["work"]: w for w in combine(rows, "median")}
    assert list(works) == ["Rusalka", "Symphony", "Humoresque"]  # longest first
    assert works["Symphony"]["duration_ms"] == 1_300_000
    assert works["Symphony"]["num_movements"] == 2
    assert works["Symphony"]["count_with_length"] == 9
    assert works["Rusalka"]["num_movements"] == 2
    assert works["Humoresque"]["num_movements"] is None
    assert works["Humoresque"]["duration"] == "3:00"


def test_clean_works_cli_filters_short_works(tmp_path):
    source = tmp_path / "dvorak.csv"
    with source.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(raw("x", 1, 1)))
        writer.writeheader()
        writer.writerows(
            [raw("Long", 1_200_000, 3), raw("Short", 300_000, 3), raw("None", None, 0)]
        )
    out = tmp_path / "works.csv"
    subprocess.run(
        [sys.executable, "-m", "pipeline.clean_works", source, "--out", out, "--min", "10:00"],
        check=True,
        capture_output=True,
    )
    with out.open(encoding="utf-8") as f:
        kept = list(csv.DictReader(f))
    assert [w["work"] for w in kept] == ["Long"]
    assert kept[0]["composer"] == "Antonín Dvořák"
    assert kept[0]["duration"] == "20:00"
