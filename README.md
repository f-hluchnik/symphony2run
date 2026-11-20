# Symphony to run

Tell it how long you're going to run and it suggests classical works of about
that length (±5 %). Live at https://symphony2run.fly.dev.

One process does everything: FastAPI serves the API under `/api` and the built
Vue frontend from `/`. Works live in SQLite, filled from the CSV files in
`backend/data/works/`.

```
backend/
  app/            the API: models.py (the schema), main.py (endpoints), bootstrap.py
  alembic/        database migrations
  data/works/     one CSV per composer, imported at startup
  pipeline/       scripts that make those CSV files from MusicBrainz
  tests/
frontend/         Vue 3 + Vite
```

## Running it locally

You need Python 3.12 and Node 22.

```sh
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m app.bootstrap                  # creates backend/db/symphonies.db
ADMIN_SECRET=dev uvicorn app.main:app --reload
```

In a second terminal:

```sh
cd frontend
npm ci
npm run dev                              # http://localhost:5173, /api goes to :8000
```

Settings come from environment variables, all optional locally:

| Variable        | Default                       |                                   |
| --------------- | ----------------------------- | --------------------------------- |
| `ADMIN_SECRET`  | none (admin disabled)         | password for the admin mode       |
| `DATABASE_PATH` | `backend/db/symphonies.db`    | `/app/db/symphonies.db` on Fly    |
| `WORKS_DIR`     | `backend/data/works`          |                                   |
| `STATIC_DIR`    | `frontend/dist`               | the built frontend, if present    |

## Tests

```sh
cd backend && pytest
```

GitHub Actions runs them, and builds the frontend, on every pull request and
push. A push to `main` then deploys.

## Deploying

Merging to `main` deploys to Fly.io (`.github/workflows/fly-deploy.yml`, using
the `FLY_API_TOKEN` repository secret). To deploy by hand: `fly deploy`.

The machine suspends when idle and wakes on the next request, so it costs
little more than its storage. On every start, `python -m app.bootstrap`:

1. creates the database if the volume is empty, otherwise applies any new
   migrations;
2. imports works from `data/works/` that aren't in the database yet. It only
   ever adds: existing works, and your verified/excluded marks, are untouched.

The admin secret is a Fly secret: `fly secrets set ADMIN_SECRET=...`.

## Admin mode

Click the small dot at the bottom of the page and enter the admin secret. You
can then mark a work as verified ("I've run to this") or exclude it from
suggestions. Excluded works stay visible to you, greyed out, so you can bring
them back.

Marks live only in the production database. Fly keeps daily snapshots of the
volume for 5 days; to keep them longer, see `fly volumes update --help`
(`--snapshot-retention`). To take a copy:

```sh
fly ssh sftp get /app/db/symphonies.db
```

## Adding a composer

Run from `backend/`, with the dev requirements installed.

```sh
python -m pipeline.fetch_musicbrainz "Antonín Dvořák"   # -> data/raw/dvorak.csv
python -m pipeline.clean_works data/raw/dvorak.csv      # -> data/works/dvorak.csv
```

1. **fetch_musicbrainz** downloads every work MusicBrainz has for the composer,
   with the lengths of all its recordings. It's slow (MusicBrainz allows one
   request per second): minutes for most composers, an hour for Mozart. To
   look at one work first: `--work "Symphony no. 9"`.
2. **clean_works** adds movements up into whole works, using the median
   recording length (`--stat` to change), and drops works under 10 minutes
   (`--min`).
3. Skim the result. Sums are only as good as the titles in MusicBrainz: when a
   movement is listed under two different names, the work comes out too long.
   Fix or delete such rows by hand.
4. Commit `data/works/dvorak.csv` and merge. The new works appear after the
   deploy. `data/raw/` is not committed.

The composer's name is taken from MusicBrainz and becomes the name in the
composer filter.

## Changing the schema

`backend/app/models.py` is the only place the schema is defined. New databases
are created from it, and migrations are generated from changes to it:

```sh
cd backend
# edit app/models.py, then:
alembic revision --autogenerate -m "add tempo column"
# read the generated file in alembic/versions/, then:
alembic upgrade head
pytest
```

Production applies the migration on the next deploy.
