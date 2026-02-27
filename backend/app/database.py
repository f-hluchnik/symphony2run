import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Engine: the core connection to your DB
DB_PATH = os.path.join(os.path.dirname(__file__), '../db/symphonies.db')
SQLALCHEMY_DATABASE_URL = f'sqlite:///{DB_PATH}'

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={'check_same_thread': False}
)

# 2. SessionLocal: a factory to create session objects
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Base class for models
Base = declarative_base()

# 4. Dependency for FastAPI endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()