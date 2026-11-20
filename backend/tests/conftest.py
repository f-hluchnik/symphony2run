import os
import tempfile
from pathlib import Path

# Settings are read when the app is imported, so point them at throwaway
# locations before any test module imports it.
_tmp = Path(tempfile.mkdtemp(prefix="symphony2run-tests-"))
os.environ["DATABASE_PATH"] = str(_tmp / "test.db")
os.environ["WORKS_DIR"] = str(_tmp / "works")
os.environ["STATIC_DIR"] = str(_tmp / "static")
os.environ["ADMIN_SECRET"] = "test-secret"

(_tmp / "static").mkdir()
(_tmp / "static" / "index.html").write_text("<title>Symphony2Run</title>")
(_tmp / "works").mkdir()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

ADMIN = {"x-admin-secret": "test-secret"}

# 150 works spread evenly over 19:00-20:59, the whole ±5 % window around a
# 20-minute run (more than 100, which exposed an old bug), plus a few that don't fit.
WORKS = [("Composer A", f"Work {i}", 19 * 60_000 + i * 800) for i in range(150)] + [
    ("Composer B", "Too short", 10 * 60_000),
    ("Composer B", "Too long", 40 * 60_000),
    ("Composer B", "Twenty minutes", 20 * 60_000),
]


def write_works_csv(path: Path, works: list[tuple[str, str, int]]) -> None:
    lines = ["composer,work,duration_ms"] + [f'{c},"{w}",{ms}' for c, w, ms in works]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def reset_database() -> None:
    """Delete the test database; pooled connections would keep the old file alive."""
    from app.database import engine
    from app.settings import DATABASE_PATH

    engine.dispose()
    DATABASE_PATH.unlink(missing_ok=True)


@pytest.fixture
def client():
    """A fresh database with WORKS, prepared exactly like at startup."""
    from app import bootstrap
    from app.settings import WORKS_DIR

    reset_database()
    write_works_csv(WORKS_DIR / "test.csv", WORKS)
    bootstrap.prepare_database()

    from app.main import app

    with TestClient(app) as client:
        yield client
