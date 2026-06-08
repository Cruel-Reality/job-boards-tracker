"""Greenhouse job board source: fetch postings and normalize them to JobBase."""

import httpx

from app.models import JobBase


def build_jobs_url(board_token: str) -> str:
    return f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"


def normalize_job(raw: dict, company: str) -> JobBase:
    """Map one raw Greenhouse job dict to our normalized JobBase schema."""
    location = raw.get("location") or {}
    location_name = location.get("name")

    # Greenhouse sometimes omits company_name; fall back to the tracked name.
    company_name = raw.get("company_name") or company

    return JobBase(
        source="greenhouse",
        source_job_id=str(raw["id"]),
        company=company_name,
        title=raw["title"],
        url=raw["absolute_url"],
        location=location_name,
        # greenhouse does not usually have salary info
        salary_min=None,
        salary_max=None,
        currency=None,
        is_remote=None,
    )


async def fetch_greenhouse_jobs(board_token: str, company: str) -> list[JobBase]:
    """Fetch and normalize all jobs for a board.

    Raises httpx.HTTPStatusError on a non-2xx response (callers like /ingest/all
    catch this to record a failed company without aborting the whole run).
    """
    url = build_jobs_url(board_token)

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url)

    response.raise_for_status()
    data = response.json()

    raw_jobs = data.get("jobs", [])
    return [normalize_job(job, company=company) for job in raw_jobs]
