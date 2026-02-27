from sqlalchemy import Column, Integer, String
from .database import Base

class Work(Base):
    __tablename__ = 'works'
    
    id = Column(Integer, primary_key=True, index=True)
    composer = Column(String)
    work = Column(String)
    duration_ms = Column(Integer, index=True)