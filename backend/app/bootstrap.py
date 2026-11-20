"""Bring the database up to date before the server starts.

    python -m app.bootstrap

- No database yet: create it from the model (app/models.py) and mark it as
  being at the latest migration.
- Existing database: apply any pending Alembic migrations.
- Then import new works from data/works/ (see app/works_import.py).
"""

import logging

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from .database import SessionLocal, engine
from .models import Base, Work
from .settings import ALEMBIC_INI, DATABASE_PATH, WORKS_DIR
from .works_import import import_works

log = logging.getLogger("app.bootstrap")


def prepare_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    alembic = Config(str(ALEMBIC_INI))

    if inspect(engine).has_table(Work.__tablename__):
        command.upgrade(alembic, "head")
    else:
        log.info("Creating a new database at %s", DATABASE_PATH)
        Base.metadata.create_all(engine)
        command.stamp(alembic, "head")

    with SessionLocal() as db:
        added = import_works(db, WORKS_DIR)
    log.info("Imported %d new works from %s", added, WORKS_DIR)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    prepare_database()
