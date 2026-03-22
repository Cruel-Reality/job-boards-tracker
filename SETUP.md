# Local Setup

## 1. Clone repo
git clone <repo-url>
cd job-boards-tracker

## 2. Setup environment
uv venv
source .venv/bin/activate
uv sync

## 3. Configure environment
cp .env.example .env

## 4. Setup Postgres
# Ensure Postgres is running and create DB
createdb job_tracker

## 5. Apply migrations
alembic upgrade head

## 6. Run app
uvicorn app.main:app --reload
