"""Database schema. This module is the single definition of the schema:
fresh databases are created from it, and Alembic migrations are generated
from changes to it (see README, "Changing the schema")."""

from sqlalchemy import Index, Text, UniqueConstraint, false
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Work(Base):
    __tablename__ = "works"
    __table_args__ = (
        UniqueConstraint("composer", "work"),
        Index("idx_duration", "duration_ms"),
        {"sqlite_autoincrement": True},
    )

    # Declared nullable only to match the existing table's DDL ("id INTEGER
    # PRIMARY KEY AUTOINCREMENT"); SQLite never lets this rowid alias be NULL.
    id: Mapped[int] = mapped_column(primary_key=True, nullable=True)
    composer: Mapped[str] = mapped_column(Text)
    work: Mapped[str] = mapped_column(Text)
    duration_ms: Mapped[int]
    # Set by the admin: "I've run to this" / "not suitable, hide it".
    verified: Mapped[bool] = mapped_column(default=False, server_default=false())
    excluded: Mapped[bool] = mapped_column(default=False, server_default=false())
