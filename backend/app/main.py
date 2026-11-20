import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import get_db
from .models import Work
from .schemas import WorkSchema
from .settings import STATIC_DIR, admin_secret

# A search matches works within ±5 % of the run's duration.
DURATION_TOLERANCE = 0.05
SUGGESTIONS = 5

app = FastAPI(title="Symphony2Run")
router = APIRouter(prefix="/api")

DB = Annotated[Session, Depends(get_db)]


def is_admin(x_admin_secret: Annotated[str | None, Header()] = None) -> bool:
    secret = admin_secret()
    return bool(secret and x_admin_secret and secrets.compare_digest(x_admin_secret, secret))


def require_admin(admin: Annotated[bool, Depends(is_admin)]) -> None:
    if not admin:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/")
def root() -> dict[str, str]:
    return {"message": "Welcome. Please enter the duration of your run."}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/composers/")
def get_composers(db: DB) -> list[str]:
    return list(db.scalars(select(Work.composer).distinct().order_by(Work.composer)))


@router.get("/search/")
def search(
    db: DB,
    admin: Annotated[bool, Depends(is_admin)],
    run_duration: Annotated[int, Query(ge=1, le=24 * 60, description="Minutes")],
    composers: Annotated[list[str], Query()] = [],  # noqa: B006 (FastAPI copies it)
    verified_only: bool = False,
) -> list[WorkSchema]:
    """Up to five random works whose duration fits the run.

    The admin also sees excluded works, so an exclusion can be undone.
    """
    run_ms = run_duration * 60_000
    query = select(Work).where(
        Work.duration_ms.between(
            int(run_ms * (1 - DURATION_TOLERANCE)), int(run_ms * (1 + DURATION_TOLERANCE))
        )
    )
    if not admin:
        query = query.where(Work.excluded.is_(False))
    if composers:
        query = query.where(Work.composer.in_(composers))
    if verified_only:
        query = query.where(Work.verified.is_(True))
    return list(db.scalars(query.order_by(func.random()).limit(SUGGESTIONS)))


@router.get("/admin/verify", dependencies=[Depends(require_admin)])
def verify_admin() -> dict[str, bool]:
    return {"ok": True}


def _set_flag(db: Session, work_id: int, flag: str, value: bool) -> dict:
    work = db.get(Work, work_id)
    if work is None:
        raise HTTPException(status_code=404, detail="Work not found")
    setattr(work, flag, value)
    db.commit()
    return {"id": work_id, flag: value}


@router.patch("/works/{work_id}/verified", dependencies=[Depends(require_admin)])
def set_verified(work_id: int, value: bool, db: DB) -> dict:
    return _set_flag(db, work_id, "verified", value)


@router.patch("/works/{work_id}/excluded", dependencies=[Depends(require_admin)])
def set_excluded(work_id: int, value: bool, db: DB) -> dict:
    return _set_flag(db, work_id, "excluded", value)


app.include_router(router)

# The built frontend, served from the same origin as the API. Mounted last so
# /api routes take precedence. Absent in local development (Vite serves it).
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
