import random
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from .models import Work
from .database import get_db
from .schemas import WorkSchema
from fastapi.middleware.cors import CORSMiddleware
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173'], # The address where Vue runs
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.get('/')
async def root():
    return {'message': 'Welcome. Please enter the duration of your run.'}

@app.get('/search/', response_model=List[WorkSchema])
async def get_symphony(run_duration: int, db: Session = Depends(get_db)) -> str:
    run_duration_ms = run_duration * 60000
    min_duration = int(run_duration_ms * 0.95)
    max_duration = int(run_duration_ms * 1.05)
    skip = 0
    limit = 100
    results = (
        db.query(Work)
        .filter(Work.duration_ms.between(min_duration, max_duration))
        .offset(skip)
        .limit(limit)
        .all()
    )
    results_sample = random.sample(results, min(5, len(results)))

    return results_sample

@app.get('/works/')
def read_works(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(Work).offset(skip).limit(limit).all()