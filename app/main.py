import time

from fastapi import FastAPI, HTTPException, Path, Query

from app.models import CanonicalJob, ServiceInfo
from app.repository import get_job, get_jobs, upsert_job
from app.sources.greenhouse import fetch_greenhouse_jobs

START_TIME = time.time()
VERSION = "0.1.0"

app = FastAPI(title="Job Board Tracker")


@app.get("/health", status_code=200)
def health():
    return ServiceInfo(
        status="healthy",
        service="Job Board Tracker",
        uptime_seconds=int(time.time() - START_TIME),
        version=VERSION,
    )


@app.get("/sources/greenhouse", response_model=list[CanonicalJob])
async def greenhouse(
    board: str = Query(
        ...,
        description="Greenhouse board token (ex: 'stripe' from boards.greenhouse.io/stripe)",
    ),
    company: str = Query(
        ...,
        description="Company name (ex: 'Stripe')",
    ),
) -> list[CanonicalJob]:
    jobs = await fetch_greenhouse_jobs(board_token=board, company=company)
    for job in jobs:
        upsert_job(job)
    return jobs


@app.get("/jobs", response_model=list[CanonicalJob])
def jobs(
    company: str | None = Query(None, description="Filter by company ex: 'Stripe'"),
    limit: int = Query(25, ge=1, le=100),
) -> list[CanonicalJob]:
    return get_jobs(company=company, limit=limit)


@app.get("/jobs/{db_id}", response_model=CanonicalJob)
def job(
    db_id: int = Path(..., ge=1, description="database primary key"),
) -> CanonicalJob:
    job = get_job(db_id=db_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"No job with id: {db_id} found")

    return job
