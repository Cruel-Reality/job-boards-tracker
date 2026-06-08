# Job Boards Tracker

![CI](https://github.com/Cruel-Reality/job-boards-tracker/actions/workflows/ci.yml/badge.svg)

A FastAPI backend that ingests job postings from company job boards (currently
[Greenhouse](https://www.greenhouse.io/)), normalizes them into a consistent schema, and stores
them in Postgres for querying and application tracking.

## Stack

- Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic
- Postgres 16 (via Docker) · psycopg 3
- uv (dependency/project management) · Ruff (lint/format) · pytest

## Quickstart

Requires [uv](https://docs.astral.sh/uv/) and [Docker](https://docs.docker.com/get-docker/).

```bash
cp .env.example .env                   # configure environment
docker compose up -d db                # start Postgres (wait for it to be healthy)
uv sync                                # install dependencies
uv run alembic upgrade head            # apply migrations
uv run uvicorn app.main:app --reload   # run the API
```

Interactive API docs: http://127.0.0.1:8000/docs

## Configuration

Copy `.env.example` to `.env` and adjust as needed. `.env` is gitignored and must never be committed.

| Variable       | Description                                              | Default                                                              |
| -------------- | -------------------------------------------------------- | -------------------------------------------------------------------- |
| `DATABASE_URL` | Postgres connection string (matches the compose db).     | `postgresql+psycopg://job_user:devpassword@localhost:5432/job_tracker` |
| `SQL_ECHO`     | When truthy, log every SQL statement (debugging).        | `false`                                                              |

## Common commands

```bash
uv run pytest                # run tests
uv run ruff check .          # lint
uv run ruff format .         # format
uv run alembic current       # show current migration
docker compose down          # stop Postgres (keeps data)
docker compose down -v       # stop Postgres and wipe data
```

## API overview

| Method   | Path                       | Description                                  |
| -------- | -------------------------- | -------------------------------------------- |
| `GET`    | `/health`                  | Service status                               |
| `GET`    | `/sources/greenhouse`      | Fetch + store jobs for a Greenhouse board    |
| `POST`   | `/ingest/all`              | Ingest jobs for all tracked companies        |
| `GET`    | `/jobs`                    | List jobs (filter by company, unapplied)     |
| `GET`    | `/jobs/{id}`               | Get a single job                             |
| `GET`    | `/companies`               | List tracked companies                       |
| `POST`   | `/company`                 | Add a tracked company                        |
| `DELETE` | `/companies/{id}`          | Delete a company and its jobs                 |
| `GET`    | `/applications`            | List job applications                        |
| `POST`   | `/applications`            | Track an application for a job               |
| `PATCH`  | `/applications/{id}`       | Update an application                        |

List endpoints (`/jobs`, `/companies`, `/applications`) are paginated: pass `limit` and `offset`,
and the response is an envelope — `{ "items": [...], "total", "limit", "offset", "has_more" }`.

## Project layout

```
app/
  main.py          FastAPI routes
  models.py        Pydantic schemas
  orm_models.py    SQLAlchemy models
  repository.py    DB access layer
  db.py            engine / session setup
  sources/         job board source adapters (greenhouse.py)
alembic/           database migrations
tests/             pytest suite
```
