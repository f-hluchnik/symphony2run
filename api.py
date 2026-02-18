from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # The address where Vue runs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome. Please enter the duration of your run."}

fake_symphonies = {
    "Beethoven Symphony in A major": 40,
    "Mozart Symphony in C minor": 43,
    "Beethoven Symphony in G minor": 31,
    "Mozart Symphony in G minor": 49,
}

@app.get("/run/")
async def get_symphony(run_duration: int) -> str:
    for name, duration in fake_symphonies.items():
        min = run_duration - 3
        max = run_duration + 3
        if min <= duration <= max:
            return f'For your {run_duration} minutes run, we recommend {name} with length of {duration} minutes.'
    return 'There is no suitable symphony for your run.'