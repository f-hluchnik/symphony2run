import os, random
from fastapi import APIRouter, FastAPI, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from .models import Work
from .database import get_db
from .schemas import WorkSchema
from fastapi.middleware.cors import CORSMiddleware
from typing import List

app = FastAPI()

origins = os.getenv('ALLOW_ORIGINS', 'http://localhost:5173').split(',')

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

router = APIRouter(prefix='/api')

def require_admin(x_admin_secret: str = Header(...)):
    secret = os.getenv('ADMIN_SECRET')
    if not secret or x_admin_secret != secret:
        raise HTTPException(status_code=403, detail='Forbidden')
    
@router.get('/admin/verify', dependencies=[Depends(require_admin)])
async def verify_admin():
    return {'ok': True}

@router.get('/')
async def root():
    return {'message': 'Welcome. Please enter the duration of your run.'}

@router.get('/health')
async def health():
    return {'status': 'ok'}

@router.get('/composers/', response_model=List[str])
async def get_composers(db: Session = Depends(get_db)):
    rows = db.query(Work.composer).distinct().order_by(Work.composer).all()
    return [r[0] for r in rows]

@router.get('/search/', response_model=List[WorkSchema])
async def get_symphony(
    run_duration: int,
    composers: List[str] = Query(default=[]),
    verified_only: bool = False,
    db: Session = Depends(get_db)
) -> str:
    run_duration_ms = run_duration * 60000
    min_duration = int(run_duration_ms * 0.95)
    max_duration = int(run_duration_ms * 1.05)

    query = (
        db.query(Work)
        .filter(Work.duration_ms.between(min_duration, max_duration))
        .filter(Work.excluded == False)
    )
    if composers:
        query = query.filter(Work.composer.in_(composers))
    if verified_only:
        query = query.filter(Work.verified == True)

    results = query.limit(100).all()
    return random.sample(results, min(5, len(results)))

@router.patch('/works/{work_id}/verified', dependencies=[Depends(require_admin)])
async def set_verified(work_id: int, value: bool, db: Session = Depends(get_db)):
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail='Work not found')
    work.verified = value
    db.commit()
    return {'id': work_id, 'verified': value}


@router.patch('/works/{work_id}/excluded', dependencies=[Depends(require_admin)])
async def set_excluded(work_id: int, value: bool, db: Session = Depends(get_db)):
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail='Work not found')
    work.excluded = value
    db.commit()
    return {'id': work_id, 'excluded': value}

@router.get('/works/')
def read_works(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(Work).offset(skip).limit(limit).all()

app.include_router(router)