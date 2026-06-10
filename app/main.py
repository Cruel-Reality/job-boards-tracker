"""FastAPI application: HTTP routes for jobs, companies, and applications.

Routes stay thin: request validation and response shaping only, and delegate all
database work to app.repository.
"""

import logging
import time

from fastapi import Depends, FastAPI, HTTPException, Path, Query, status

from app.auth import require_api_key

from app.models import (
    CompanyCreate,
    CompanyOut,
    JobApplicationCreate,
    JobApplicationOut,
    JobApplicationUpdate,
    JobApplicationWithJobOut,
    JobBase,
    JobOut,
    Page,
    ServiceInfo,
    StatsOut,
)
from app.orm_models import (
    JobCategoryEnum,
    JobStatusEnum,
    SectorEnum,
    SeniorityEnum,
    SizeEnum,
)
from app.repository import (
    add_application,
    add_company,
    delete_application_by_id,
    delete_company_by_id,
    delete_job_by_id,
    get_applications,
    get_companies,
    get_job,
    get_jobs,
    get_stats,
    mark_company_synced,
    update_application,
    upsert_jobs,
)
from app.sources.greenhouse import fetch_greenhouse_jobs

logger = logging.getLogger(__name__)

START_TIME = time.time()
VERSION = "0.1.0"

SOURCE_FETCHERS = {
    "greenhouse": fetch_greenhouse_jobs,
}

app = FastAPI(title="Job Board Tracker")


@app.get("/sources", response_model=list[str])
def sources():
    """Source identifiers we can actually ingest (the keys of SOURCE_FETCHERS).

    The frontend uses this to populate its source dropdown, so a company can only
    be added with a source the backend knows how to fetch.
    """
    return sorted(SOURCE_FETCHERS)


@app.get("/health", status_code=200)
def health():
    return ServiceInfo(
        status="healthy",
        service="Job Board Tracker",
        uptime_seconds=int(time.time() - START_TIME),
        version=VERSION,
    )


@app.get(
    "/sources/greenhouse",
    response_model=list[JobBase],
    dependencies=[Depends(require_api_key)],
)
async def greenhouse(
    board: str = Query(
        ...,
        description="Greenhouse board token (ex: 'stripe' from boards.greenhouse.io/stripe)",
    ),
    company: str = Query(
        ...,
        description="Company name (ex: 'Stripe')",
    ),
) -> list[JobBase]:
    jobs = await fetch_greenhouse_jobs(board_token=board, company=company)
    upsert_jobs(jobs)
    return jobs


@app.get("/jobs", response_model=Page[JobOut])
def jobs(
    company: str | None = Query(None, description="Filter by company ex: 'Stripe'"),
    limit: int = Query(25, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Number of rows to skip"),
    tracked: bool | None = Query(
        None,
        description="True: only jobs with an application; False: only jobs without one",
    ),
    application_status: JobStatusEnum | None = Query(
        None,
        description="Filter by application status (applied, unapplied, rejected, offer)",
    ),
    size: SizeEnum | None = Query(None, description="Filter by company size"),
    sector: SectorEnum | None = Query(None, description="Filter by company sector"),
    category: JobCategoryEnum | None = Query(
        None, description="Filter by job function (ex: software_engineering, data)"
    ),
    seniority: SeniorityEnum | None = Query(
        None, description="Filter by seniority bucket (ex: senior, staff, manager)"
    ),
    location: str | None = Query(
        None, description="Case-insensitive substring match on location"
    ),
    remote: bool | None = Query(
        None, description="True: only remote jobs; False: only non-remote"
    ),
    search: str | None = Query(
        None, description="Case-insensitive substring match on job title"
    ),
) -> Page[JobOut]:
    items, total = get_jobs(
        company=company,
        limit=limit,
        offset=offset,
        tracked=tracked,
        application_status=application_status,
        size=size,
        sector=sector,
        category=category,
        seniority=seniority,
        location=location,
        is_remote=remote,
        search=search,
    )
    return Page[JobOut](
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(items) < total,
    )


@app.get("/jobs/{db_id}", response_model=JobOut)
def job(
    db_id: int = Path(..., ge=1, description="database primary key"),
) -> JobOut:
    job = get_job(db_id=db_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"No job with id: {db_id} found")

    return job


@app.delete("/jobs/{db_id}", dependencies=[Depends(require_api_key)])
def delete_job(db_id: int):
    if not delete_job_by_id(db_id):
        raise HTTPException(status_code=404, detail=f"No job with id: {db_id} found")
    return {"status": "deleted"}


@app.get("/stats", response_model=StatsOut)
def stats():
    return get_stats()


@app.get("/companies", response_model=Page[CompanyOut])
def companies(
    limit: int = Query(100, ge=1, le=500, description="Page size"),
    offset: int = Query(0, ge=0, description="Number of rows to skip"),
) -> Page[CompanyOut]:
    items, total = get_companies(limit=limit, offset=offset)
    return Page[CompanyOut](
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(items) < total,
    )


@app.post(
    "/company",
    response_model=CompanyOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
async def create_company(company: CompanyCreate):
    # Reject sources we can't ingest, so a typo like "linkedin" never reaches the DB
    # and silently get skipped by /ingest/all.
    fetcher = SOURCE_FETCHERS.get(company.source)
    if fetcher is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported source '{company.source}'. "
            f"Supported sources: {sorted(SOURCE_FETCHERS)}",
        )

    # Validate the board by test-fetching it, so a wrong slug is caught now instead
    # of silently producing no jobs at ingest time. A real board with zero open
    # roles still fetches successfully, so only a failed fetch is rejected.
    try:
        await fetcher(board_token=company.board, company=company.company)
    except Exception:
        logger.warning(
            "Board validation failed for source=%s board=%s",
            company.source,
            company.board,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Could not load a '{company.source}' board for '{company.board}'. "
            f"Check the slug (e.g. boards.greenhouse.io/<slug>).",
        ) from None

    new_company = add_company(company)
    if new_company is None:
        raise HTTPException(
            status_code=400,
            detail="Company with this source and board already exists",
        )
    return new_company


@app.post("/ingest/all", dependencies=[Depends(require_api_key)])
async def ingest_all():
    # Ingest sequentially for every tracked company. Capped at 500 to bound the
    # work in one request; companies fetch one at a time to stay simple and gentle
    # on source rate limits. A failing company is recorded, not fatal.
    companies, _ = get_companies(limit=500)

    total_jobs = 0
    successful_companies = 0
    failed_companies = []

    for company in companies:
        fetcher = SOURCE_FETCHERS.get(company.source)
        if fetcher is None:
            continue
        try:
            jobs = await fetcher(
                board_token=company.board,
                company=company.company,
            )
            upsert_jobs(jobs, company_id=company.id)
            mark_company_synced(company.id)
            total_jobs += len(jobs)
            successful_companies += 1
        except Exception:
            logger.exception(
                "Ingest failed for company=%s source=%s board=%s",
                company.company,
                company.source,
                company.board,
            )
            failed_companies.append(
                {
                    "company": company.company,
                    "source": company.source,
                    "board": company.board,
                }
            )
            continue

    return {
        "successful_companies": successful_companies,
        "jobs_fetched": total_jobs,
        "failed_companies": failed_companies,
    }


@app.delete("/companies/{db_id}", dependencies=[Depends(require_api_key)])
def delete_company(db_id: int):
    deleted = delete_company_by_id(db_id)

    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"No company with id: {db_id} found"
        )

    return {"status": "deleted"}


@app.post(
    "/applications",
    response_model=JobApplicationOut,
    dependencies=[Depends(require_api_key)],
)
def create_application(app_in: JobApplicationCreate):
    new_app = add_application(app_in)

    if new_app is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if new_app == "duplicate":
        raise HTTPException(
            status_code=400, detail="Application already exists for this job"
        )

    return new_app


@app.get("/applications", response_model=Page[JobApplicationWithJobOut])
def read_applications(
    limit: int = Query(100, ge=1, le=500, description="Page size"),
    offset: int = Query(0, ge=0, description="Number of rows to skip"),
    status_filter: JobStatusEnum | None = Query(
        None, description="Filter by application status"
    ),
) -> Page[JobApplicationWithJobOut]:
    items, total = get_applications(limit=limit, status=status_filter, offset=offset)
    return Page[JobApplicationWithJobOut](
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(items) < total,
    )


@app.patch(
    "/applications/{application_id}",
    response_model=JobApplicationOut,
    dependencies=[Depends(require_api_key)],
)
def patch_application(application_id: int, app_update: JobApplicationUpdate):
    updated_app = update_application(application_id, app_update)

    if updated_app is None:
        raise HTTPException(
            status_code=404, detail=f"No application with id: {application_id} found"
        )

    return updated_app


@app.delete("/applications/{application_id}", dependencies=[Depends(require_api_key)])
def delete_application(application_id: int):
    if not delete_application_by_id(application_id):
        raise HTTPException(
            status_code=404, detail=f"No application with id: {application_id} found"
        )
    return {"status": "deleted"}
