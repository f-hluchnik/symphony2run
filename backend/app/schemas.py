from pydantic import BaseModel

class WorkSchema(BaseModel):
    id: int
    composer: str
    work: str
    duration_ms: int

    class Config:
        orm_mode = True