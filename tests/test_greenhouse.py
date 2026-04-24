from unittest.mock import AsyncMock, MagicMock, patch

from app.sources.greenhouse import build_jobs_url, fetch_greenhouse_jobs, normalize_job


def test_build_jobs_url():
    assert build_jobs_url("stripe") == "https://boards-api.greenhouse.io/v1/boards/stripe/jobs"


def test_normalize_job_full():
    raw = {
        "id": 123,
        "title": "Software Engineer",
        "absolute_url": "https://boards.greenhouse.io/stripe/jobs/123",
        "location": {"name": "New York, NY"},
        "company_name": "Stripe Inc",
    }
    job = normalize_job(raw, company="Stripe")

    assert job.source == "greenhouse"
    assert job.source_job_id == "123"
    assert job.company == "Stripe Inc"
    assert job.title == "Software Engineer"
    assert job.url == "https://boards.greenhouse.io/stripe/jobs/123"
    assert job.location == "New York, NY"
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.currency is None
    assert job.is_remote is None


def test_normalize_job_uses_fallback_company_when_company_name_absent():
    raw = {
        "id": 456,
        "title": "Engineer",
        "absolute_url": "https://example.com/job",
        "location": {},
        "company_name": None,
    }
    job = normalize_job(raw, company="Acme Corp")
    assert job.company == "Acme Corp"


def test_normalize_job_no_location():
    raw = {
        "id": 789,
        "title": "Designer",
        "absolute_url": "https://example.com/job",
        "location": None,
        "company_name": "ACME",
    }
    job = normalize_job(raw, company="ACME")
    assert job.location is None


async def test_fetch_greenhouse_jobs_returns_normalized_jobs():
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "jobs": [
            {
                "id": 1,
                "title": "Engineer",
                "absolute_url": "https://example.com/jobs/1",
                "location": {"name": "Remote"},
                "company_name": "TestCo",
            }
        ]
    }

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("app.sources.greenhouse.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        jobs = await fetch_greenhouse_jobs("testco", "TestCo")

    assert len(jobs) == 1
    assert jobs[0].source == "greenhouse"
    assert jobs[0].source_job_id == "1"
    assert jobs[0].title == "Engineer"
    assert jobs[0].company == "TestCo"
    assert jobs[0].location == "Remote"


async def test_fetch_greenhouse_jobs_empty_board():
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"jobs": []}

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    with patch("app.sources.greenhouse.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        jobs = await fetch_greenhouse_jobs("empty-board", "NoJobs Corp")

    assert jobs == []
