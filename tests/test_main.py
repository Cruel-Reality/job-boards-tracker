from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.models import CompanyOut, JobApplicationOut, JobApplicationWithJobOut, JobOut
from app.orm_models import JobStatusEnum

client = TestClient(app)


# ─── helpers ──────────────────────────────────────────────────────────────────


def make_job_out(**kwargs) -> JobOut:
    defaults = dict(
        id=1,
        source="greenhouse",
        source_job_id="job-1",
        company="Acme",
        title="Engineer",
        url="https://example.com/jobs/1",
        location="Remote",
        salary_min=None,
        salary_max=None,
        currency=None,
        is_remote=None,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )
    return JobOut(**{**defaults, **kwargs})


def make_company_out(**kwargs) -> CompanyOut:
    defaults = dict(
        id=1,
        source="greenhouse",
        company="Acme",
        board="acme",
        sector=None,
        size=None,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )
    return CompanyOut(**{**defaults, **kwargs})


def make_application_out(**kwargs) -> JobApplicationOut:
    defaults = dict(
        id=1,
        job_posting_id=1,
        status=JobStatusEnum.applied,
        notes=None,
        applied_at=None,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )
    return JobApplicationOut(**{**defaults, **kwargs})


# ─── health ───────────────────────────────────────────────────────────────────


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Job Board Tracker"
    assert data["version"] == "0.1.0"
    assert "uptime_seconds" in data


# ─── jobs ─────────────────────────────────────────────────────────────────────


def test_get_jobs_returns_list():
    with patch("app.main.get_jobs", return_value=[make_job_out()]):
        response = client.get("/jobs")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Engineer"


def test_get_jobs_passes_query_params():
    with patch("app.main.get_jobs", return_value=[]) as mock_get_jobs:
        client.get("/jobs?company=Acme&limit=10&unapplied_only=true")
    mock_get_jobs.assert_called_once_with(company="Acme", limit=10, unapplied_only=True)


def test_get_job_found():
    with patch("app.main.get_job", return_value=make_job_out(id=5)):
        response = client.get("/jobs/5")
    assert response.status_code == 200
    assert response.json()["id"] == 5


def test_get_job_not_found():
    with patch("app.main.get_job", return_value=None):
        response = client.get("/jobs/999")
    assert response.status_code == 404
    assert "999" in response.json()["detail"]


# ─── companies ────────────────────────────────────────────────────────────────


def test_get_companies():
    with patch("app.main.get_companies", return_value=[make_company_out()]):
        response = client.get("/companies")
    assert response.status_code == 200
    assert response.json()[0]["company"] == "Acme"


def test_create_company():
    with patch("app.main.add_company", return_value=make_company_out()):
        response = client.post(
            "/company", json={"source": "greenhouse", "company": "Acme", "board": "acme"}
        )
    assert response.status_code == 201
    assert response.json()["company"] == "Acme"


def test_create_company_duplicate_returns_400():
    with patch("app.main.add_company", return_value=None):
        response = client.post(
            "/company", json={"source": "greenhouse", "company": "Acme", "board": "acme"}
        )
    assert response.status_code == 400


def test_delete_company():
    with patch("app.main.delete_company_by_id", return_value=True):
        response = client.delete("/companies/1")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"


def test_delete_company_not_found():
    with patch("app.main.delete_company_by_id", return_value=False):
        response = client.delete("/companies/999")
    assert response.status_code == 404
    assert "999" in response.json()["detail"]


# ─── greenhouse source endpoint ───────────────────────────────────────────────


def test_greenhouse_endpoint():
    jobs = [make_job_out()]
    with patch("app.main.fetch_greenhouse_jobs", new=AsyncMock(return_value=jobs)), \
         patch("app.main.upsert_jobs"):
        response = client.get("/sources/greenhouse?board=stripe&company=Stripe")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_greenhouse_endpoint_requires_board_and_company():
    response = client.get("/sources/greenhouse")
    assert response.status_code == 422


# ─── ingest all ───────────────────────────────────────────────────────────────


def test_ingest_all_success():
    companies = [make_company_out()]
    jobs = [make_job_out(), make_job_out(id=2, source_job_id="job-2")]
    mock_fetcher = AsyncMock(return_value=jobs)

    with patch("app.main.get_companies", return_value=companies), \
         patch.dict("app.main.SOURCE_FETCHERS", {"greenhouse": mock_fetcher}), \
         patch("app.main.upsert_jobs"):
        response = client.post("/ingest/all")

    assert response.status_code == 200
    data = response.json()
    assert data["successful_companies"] == 1
    assert data["jobs_fetched"] == 2
    assert data["failed_companies"] == []


def test_ingest_all_records_failed_company():
    companies = [make_company_out()]
    mock_fetcher = AsyncMock(side_effect=Exception("API down"))

    with patch("app.main.get_companies", return_value=companies), \
         patch.dict("app.main.SOURCE_FETCHERS", {"greenhouse": mock_fetcher}):
        response = client.post("/ingest/all")

    assert response.status_code == 200
    data = response.json()
    assert data["successful_companies"] == 0
    assert data["jobs_fetched"] == 0
    assert len(data["failed_companies"]) == 1
    assert data["failed_companies"][0]["company"] == "Acme"


# ─── applications ─────────────────────────────────────────────────────────────


def test_create_application():
    with patch("app.main.add_application", return_value=make_application_out()):
        response = client.post("/applications", json={"job_posting_id": 1, "status": "applied"})
    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["status"] == "applied"


def test_create_application_job_not_found():
    with patch("app.main.add_application", return_value=None):
        response = client.post("/applications", json={"job_posting_id": 999, "status": "applied"})
    assert response.status_code == 404


def test_create_application_duplicate_returns_400():
    with patch("app.main.add_application", return_value="duplicate"):
        response = client.post("/applications", json={"job_posting_id": 1, "status": "applied"})
    assert response.status_code == 400


def test_get_applications():
    app_with_job = JobApplicationWithJobOut(
        id=1,
        job_posting_id=1,
        status=JobStatusEnum.applied,
        notes=None,
        applied_at=None,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
        job=make_job_out(),
    )
    with patch("app.main.get_applications", return_value=[app_with_job]):
        response = client.get("/applications")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["job"]["title"] == "Engineer"


def test_patch_application():
    with patch("app.main.update_application", return_value=make_application_out(status=JobStatusEnum.rejected)):
        response = client.patch("/applications/1", json={"status": "rejected"})
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_patch_application_not_found():
    with patch("app.main.update_application", return_value=None):
        response = client.patch("/applications/999", json={"status": "rejected"})
    assert response.status_code == 404
    assert "999" in response.json()["detail"]
