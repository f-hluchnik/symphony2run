"""Import the works CSVs (data/works/*.csv) into the database.

Insert-only: rows already in the database, matched by (composer, work), are
left untouched, so the admin's verified/excluded marks survive. Running it
again is safe, which is what lets the app import on every startup: adding a
composer is "add a CSV and deploy".
"""

import csv
import logging
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from .models import Work

log = logging.getLogger(__name__)


def read_works(path: Path) -> Iterator[dict]:
    """Rows of one CSV as Work values. Rows without a usable duration are skipped."""
    with path.open(newline="", encoding="utf-8") as f:
        for line, row in enumerate(csv.DictReader(f), start=2):
            try:
                yield {
                    "composer": row["composer"],
                    "work": row["work"],
                    "duration_ms": int(row["duration_ms"]),
                }
            except (KeyError, ValueError):
                log.warning("%s:%d: skipped, no composer, work or duration_ms", path, line)


def import_works(db: Session, directory: Path) -> int:
    """Insert works that aren't in the database yet. Returns how many were added."""
    rows = [row for path in sorted(directory.glob("*.csv")) for row in read_works(path)]
    if not rows:
        return 0
    count = select(func.count()).select_from(Work)
    before = db.scalar(count)
    db.execute(insert(Work).on_conflict_do_nothing(index_elements=["composer", "work"]), rows)
    db.commit()
    return db.scalar(count) - before
