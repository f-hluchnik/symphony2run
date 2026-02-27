# test_db.py
from database import SessionLocal
from models import Work

db = SessionLocal()

# Try reading the first 5 rows
works = db.query(Work).limit(5).all()
for w in works:
    print(w.id, w.composer, w.work, w.duration_ms)

db.close()