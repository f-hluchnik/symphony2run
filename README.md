# Symphony to run
Choose a symphony for your run.


## workflow for schema changes
cd backend
alembic revision --autogenerate -m "describe what changed"
# review the generated file in alembic/versions/
alembic upgrade head