"""Paths and secrets, from environment variables with local-development defaults."""

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

# On Fly.io this directory is the persistent volume (see fly.toml).
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", BACKEND_DIR / "db" / "symphonies.db"))

# One CSV per composer, imported into the database at startup.
WORKS_DIR = Path(os.getenv("WORKS_DIR", BACKEND_DIR / "data" / "works"))

# The built frontend. Missing in local development, where Vite serves it.
STATIC_DIR = Path(os.getenv("STATIC_DIR", BACKEND_DIR.parent / "frontend" / "dist"))

ALEMBIC_INI = BACKEND_DIR / "alembic.ini"


def admin_secret() -> str | None:
    """Read on every request rather than at import, so tests can set it."""
    return os.getenv("ADMIN_SECRET") or None
