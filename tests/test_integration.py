"""End-to-end API tests that run against a real database (CI / local test DB)."""

from fastapi.testclient import TestClient

from app.main import app
from app.models import JobApplicationCreate, JobBase
from app.orm_models import JobStatusEnum
from app.repository import add_application, get_jobs, upsert_jobs

client = TestClient(app)


def _job(source_job_id="1"):
    return JobBase(
        source="greenhouse",
        source_job_id=source_job_id,
        company="Acme",
        title="Engineer",
        url=f"https://example.com/{source_job_id}",
    )


def test_jobs_endpoint_paginates_real_data(clean_db):
    # Exercises the full path: route -> get_jobs (real DB) -> Page[JobOut].
    upsert_jobs([_job(str(i)) for i in range(3)])
    body = client.get("/jobs?limit=2&offset=0").json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["has_more"] is True


def test_jobs_endpoint_serializes_application_status(clean_db):
    upsert_jobs([_job("1")])
    jobs, _ = get_jobs()
    add_application(
        JobApplicationCreate(job_posting_id=jobs[0].id, status=JobStatusEnum.applied)
    )
    body = client.get("/jobs").json()
    assert body["items"][0]["application_status"] == "applied"


def test_applications_endpoint_serializes_nested_job(clean_db):
    # Guards the detached-instance bug: the nested JobOut.application_status must
    # resolve without a lazy load after the repository session has closed.
    upsert_jobs([_job("1")])
    jobs, _ = get_jobs()
    add_application(
        JobApplicationCreate(job_posting_id=jobs[0].id, status=JobStatusEnum.applied)
    )
    response = client.get("/applications")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["job"]["application_status"] == "applied"
