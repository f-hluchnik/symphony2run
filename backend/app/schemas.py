from pydantic import BaseModel, ConfigDict

class WorkSchema(BaseModel):
    id: int
    composer: str
    work: str
    duration_ms: int
    verified: bool
    excluded: bool

    model_config = ConfigDict(from_attributes=True)
