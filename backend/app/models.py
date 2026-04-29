from sqlalchemy import Boolean, Column, Integer, String
from .database import Base

class Work(Base):
    __tablename__ = 'works'
    
    id = Column(Integer, primary_key=True, index=True)
    composer = Column(String)
    work = Column(String)
    duration_ms = Column(Integer, index=True)
    excluded = Column(Boolean, nullable=False, default=False)
    verified = Column(Boolean, nullable=False, default=False)
