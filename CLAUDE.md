# Job Boards Tracker - Claude Instructions

## Project Purpose

This project tracks job postings from company job boards. It currently supports ingesting and normalizing jobs from Greenhouse-backed boards into a Postgres database.

The goal is to turn this into a demoable, reproducible, deployable job-tracking application with:

* FastAPI backend
* Postgres database
* SQLAlchemy ORM
* Alembic migrations
* uv for Python dependency/project management
* Ruff for linting and formatting
* Streamlit or another simple frontend
* Dockerized local development
* Clean README and setup instructions
* Additional job board sources beyond Greenhouse when practical

## Current Stack

* Python
* uv
* FastAPI
* SQLAlchemy
* Alembic
* Postgres
* psycopg 3
* python-dotenv
* Ruff
* Streamlit if present or planned

## Core Commands

Run migrations:

```bash
uv run alembic upgrade head
```

Check current migration:

```bash
uv run alembic current
```

Run API server:

```bash
uv run uvicorn app.main:app --reload
```

Open API docs:

```text
http://127.0.0.1:8000/docs
```

Run lint:

```bash
uv run ruff check .
```

Format code:

```bash
uv run ruff format .
```

Run tests:

```bash
uv run pytest
```

Run Streamlit frontend if present:

```bash
uv run streamlit run streamlit_app.py
```

If the frontend file lives somewhere else, inspect the repo and use the correct path.

## Environment

The app expects a `.env` file in the repo root.

Example local value:

```env
DATABASE_URL=postgresql+psycopg://job_user:devpassword@localhost:5432/job_tracker
```

Never commit `.env`.

Commit `.env.example` instead.

Suggested `.env.example`:

```env
DATABASE_URL=postgresql+psycopg://job_user:devpassword@localhost:5432/job_tracker
```

## Development Rules

* Do not edit unrelated files.
* Do not touch secrets, credentials, tokens, cookies, API keys, or `.env` unless explicitly asked.
* Before large changes, propose a plan.
* Prefer small, reviewable diffs.
* After changes, run Ruff.
* If tests exist, run tests.
* If tests do not exist for changed behavior, propose or add focused tests.
* Do not add new dependencies without explaining why.
* Do not silently change database models without generating or checking Alembic migrations.
* Do not use unsafe Ruff fixes unless explicitly approved.
* Preserve existing working Greenhouse ingestion and normalization behavior.
* Keep changes compatible with uv project workflow.
* Prefer `uv run ...` commands over manually activating `.venv`.

## Feature Priorities

Current highest-priority roadmap:

1. Dockerize local development with Postgres.
2. Create or improve frontend for searching, filtering, and viewing tracked jobs.
3. Improve README so a fresh clone can run the app.
4. Add `.env.example`.
5. Add deployment path.
6. Add tests around ingestion, normalization, deduplication, and API endpoints.
7. Add additional job board source support after the app is reproducible and demoable.

## Dockerization Goal

The desired local setup should eventually be:

```bash
cp .env.example .env
docker compose up -d db
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Then the API docs should be available at:

```text
http://127.0.0.1:8000/docs
```

If a Streamlit frontend exists, it should run with a documented command and connect to the backend or database cleanly.

## Frontend Goal

The frontend should make the project demoable.

Useful frontend capabilities include:

* View tracked companies
* Add or edit tracked companies if practical
* Trigger ingestion/sync for selected companies
* View normalized jobs
* Filter jobs by company, sector, size, source, location, and date
* Search job titles/descriptions
* Mark jobs as saved, ignored, applied, or interesting if that model exists or is added
* Show basic ingestion status/errors

Prefer a simple working frontend over an overdesigned UI.

## Deployment Goal

The deployment path should be simple and documented.

Preferred deployment qualities:

* Environment variables documented
* Postgres connection documented
* Migrations documented
* API start command documented
* Frontend start command documented if separate
* Clear README instructions

Avoid complex deployment architecture unless needed.

## Testing Priorities

High-value tests include:

* Greenhouse ingestion parsing
* Job normalization
* Deduplication logic
* Company config validation
* API endpoint happy paths
* API endpoint invalid payloads
* Database persistence behavior where practical

Do not create fake tests that only mirror implementation details. Tests should catch real breakage.

## Code Style

* Prefer simple, boring Python.
* Use clear function and variable names.
* Keep functions small.
* Prefer explicit data transformations over clever abstractions.
* Separate ingestion, normalization, persistence, and API layers when practical.
* Make errors visible and debuggable.
* Avoid large rewrites unless there is a clear payoff.
* Avoid premature abstraction.
* Preserve current working behavior unless intentionally changing it.

## Agent Workflow

When asked to implement a feature:

1. Inspect relevant files first.
2. Summarize the current design.
3. Propose a small implementation plan.
4. List files expected to change.
5. Wait for approval if the change is large or risky.
6. Make the smallest useful change.
7. Run Ruff.
8. Run tests if available.
9. Summarize what changed and what remains.

When asked to review code:

* Look for bugs.
* Look for broken assumptions.
* Look for missing tests.
* Look for migration issues.
* Look for environment/config problems.
* Look for overengineering.
* Look for places where the code works locally but will fail from a fresh clone.

## Known Local Database Context

Local development may use:

```env
DATABASE_URL=postgresql+psycopg://job_user:devpassword@localhost:5432/job_tracker
```

The local database can be reset manually with system Postgres commands if needed, but prefer documenting a Dockerized Postgres workflow going forward.

## Important Safety Rules

* Never print secrets.
* Never commit `.env`.
* Never commit local database dumps unless explicitly asked.
* Never modify production credentials.
* Never assume local data matters unless told.
* Before destructive database commands, explain what will be deleted.
