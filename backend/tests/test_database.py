import sqlite3
from pathlib import Path

from app import bootstrap
from app.database import SessionLocal
from app.settings import DATABASE_PATH, WORKS_DIR
from app.works_import import import_works
from tests.conftest import WORKS, reset_database, write_works_csv


def test_import_adds_new_works_and_keeps_existing_ones(client):
    with sqlite3.connect(DATABASE_PATH) as db:
        db.execute("UPDATE works SET verified = 1, excluded = 1")

    write_works_csv(WORKS_DIR / "new.csv", [("Composer C", "New work", 30 * 60_000)])
    try:
        with SessionLocal() as session:
            assert import_works(session, WORKS_DIR) == 1
            assert import_works(session, WORKS_DIR) == 0  # idempotent
    finally:
        (WORKS_DIR / "new.csv").unlink()

    with sqlite3.connect(DATABASE_PATH) as db:
        counts = db.execute("SELECT count(*), sum(verified), sum(excluded) FROM works").fetchone()
    assert counts == (len(WORKS) + 1, len(WORKS), len(WORKS))  # marks untouched


def test_rows_without_a_duration_are_skipped(tmp_path):
    (tmp_path / "bad.csv").write_text("composer,work,duration_ms\nA,No duration,\nA,Fine,600000\n")
    from app.works_import import read_works

    assert [r["work"] for r in read_works(tmp_path / "bad.csv")] == ["Fine"]


def test_existing_database_is_migrated_not_recreated():
    """The database on the Fly volume predates the model-based schema."""
    legacy = Path(__file__).parent / "legacy.sql"
    reset_database()
    with sqlite3.connect(DATABASE_PATH) as db:
        db.executescript(legacy.read_text())
    write_works_csv(WORKS_DIR / "test.csv", WORKS)

    bootstrap.prepare_database()

    with sqlite3.connect(DATABASE_PATH) as db:
        kept = db.execute("SELECT work, verified FROM works WHERE id = 1").fetchone()
        total = db.execute("SELECT count(*) FROM works").fetchone()[0]
    assert kept == ("Legacy work", 1)
    assert total == len(WORKS) + 1
