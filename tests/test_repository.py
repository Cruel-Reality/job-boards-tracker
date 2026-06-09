"""Repository tests against a real database (skipped locally without a test DB)."""

from app.models import CompanyCreate, JobApplicationCreate, JobBase
from app.orm_models import JobCategoryEnum, JobStatusEnum, SectorEnum, SizeEnum
from app.repository import (
    add_application,
    add_company,
    delete_application_by_id,
    delete_company_by_id,
    delete_job_by_id,
    get_applications,
    get_companies,
    get_jobs,
    get_stats,
    mark_company_synced,
    upsert_jobs,
)


def _job(
    source_job_id="1",
    company="Acme",
    title="Engineer",
    category=None,
    location=None,
    is_remote=None,
):
    return JobBase(
        source="greenhouse",
        source_job_id=source_job_id,
        company=company,
        title=title,
        url=f"https://example.com/{source_job_id}",
        category=category,
        location=location,
        is_remote=is_remote,
    )


def test_upsert_inserts_then_updates_same_source_job_id(clean_db):
    upsert_jobs([_job(title="Engineer")])
    jobs, total = get_jobs()
    assert total == 1
    assert jobs[0].title == "Engineer"

    # Same source + source_job_id updates the row rather than inserting a second.
    upsert_jobs([_job(title="Senior Engineer")])
    jobs, total = get_jobs()
    assert total == 1
    assert jobs[0].title == "Senior Engineer"


def test_upsert_sets_company_id(clean_db):
    company = add_company(
        CompanyCreate(source="greenhouse", company="Acme", board="acme")
    )
    upsert_jobs([_job()], company_id=company.id)
    jobs, _ = get_jobs()
    assert jobs[0].company_id == company.id


def test_get_jobs_filter_by_company(clean_db):
    upsert_jobs([_job(source_job_id="1", company="Acme")])
    upsert_jobs([_job(source_job_id="2", company="Globex")])
    jobs, total = get_jobs(company="Acme")
    assert total == 1
    assert jobs[0].company == "Acme"


def test_get_jobs_filter_by_application_status_and_tracked(clean_db):
    upsert_jobs([_job(source_job_id="1")])
    jobs, _ = get_jobs()
    add_application(
        JobApplicationCreate(job_posting_id=jobs[0].id, status=JobStatusEnum.applied)
    )

    assert get_jobs(application_status=JobStatusEnum.applied)[1] == 1
    assert get_jobs(application_status=JobStatusEnum.rejected)[1] == 0
    assert get_jobs(tracked=True)[1] == 1
    assert get_jobs(tracked=False)[1] == 0


def test_get_jobs_filter_by_size_and_sector(clean_db):
    company = add_company(
        CompanyCreate(
            source="greenhouse",
            company="Acme",
            board="acme",
            sector=SectorEnum.finance,
            size=SizeEnum.big,
        )
    )
    upsert_jobs([_job()], company_id=company.id)

    assert get_jobs(size=SizeEnum.big)[1] == 1
    assert get_jobs(size=SizeEnum.startup)[1] == 0
    assert get_jobs(sector=SectorEnum.finance)[1] == 1
    assert get_jobs(sector=SectorEnum.tech)[1] == 0


def test_get_jobs_filter_by_category(clean_db):
    upsert_jobs([_job(source_job_id="1", category=JobCategoryEnum.data)])
    upsert_jobs([_job(source_job_id="2", category=JobCategoryEnum.sales)])

    assert get_jobs(category=JobCategoryEnum.data)[1] == 1
    assert get_jobs(category=JobCategoryEnum.sales)[1] == 1
    assert get_jobs(category=JobCategoryEnum.finance)[1] == 0


def test_get_jobs_filter_by_location_substring_case_insensitive(clean_db):
    upsert_jobs([_job(source_job_id="1", location="New York, NY")])
    upsert_jobs([_job(source_job_id="2", location="San Francisco, CA")])

    # Substring and case-insensitive: "york" matches "New York, NY".
    matched, total = get_jobs(location="york")
    assert total == 1
    assert matched[0].location == "New York, NY"
    assert get_jobs(location="CA")[1] == 1
    assert get_jobs(location="Austin")[1] == 0


def test_get_jobs_filter_by_remote(clean_db):
    upsert_jobs([_job(source_job_id="1", location="Remote", is_remote=True)])
    upsert_jobs([_job(source_job_id="2", location="Boston, MA", is_remote=False)])

    assert get_jobs(is_remote=True)[1] == 1
    assert get_jobs(is_remote=False)[1] == 1
    # No filter returns both.
    assert get_jobs()[1] == 2


def test_get_jobs_pagination(clean_db):
    upsert_jobs([_job(source_job_id=str(i)) for i in range(5)])

    page1, total = get_jobs(limit=2, offset=0)
    assert total == 5
    assert len(page1) == 2

    last_page, total = get_jobs(limit=2, offset=4)
    assert total == 5
    assert len(last_page) == 1

    # Offset past the end yields no items but still reports the true total.
    empty, total = get_jobs(limit=2, offset=10)
    assert total == 5
    assert empty == []


def test_upsert_removes_stale_jobs_except_meaningful_applications(clean_db):
    company = add_company(
        CompanyCreate(source="greenhouse", company="Acme", board="acme")
    )
    upsert_jobs([_job("1"), _job("2"), _job("3"), _job("4")], company_id=company.id)
    jobs, _ = get_jobs()
    by_sid = {j.source_job_id: j for j in jobs}
    add_application(
        JobApplicationCreate(
            job_posting_id=by_sid["1"].id, status=JobStatusEnum.applied
        )
    )
    add_application(
        JobApplicationCreate(
            job_posting_id=by_sid["2"].id, status=JobStatusEnum.unapplied
        )
    )

    # Re-ingest: only "4" is still posted. "1" (applied) is stale but kept;
    # "2" (unapplied) and "3" (untracked) are stale and removed.
    upsert_jobs([_job("4")], company_id=company.id)

    remaining, _ = get_jobs()
    assert {j.source_job_id for j in remaining} == {"1", "4"}


def test_upsert_empty_fetch_skips_stale_cleanup(clean_db):
    # An empty fetch is treated as a likely failure, not an empty board, so it must
    # NOT delete the company's existing jobs.
    company = add_company(
        CompanyCreate(source="greenhouse", company="Acme", board="acme")
    )
    upsert_jobs([_job("1"), _job("2")], company_id=company.id)

    upsert_jobs([], company_id=company.id)

    _, total = get_jobs()
    assert total == 2


def test_delete_company_keeps_meaningful_applications_and_removes_the_rest(clean_db):
    company = add_company(
        CompanyCreate(source="greenhouse", company="Stripe", board="stripe")
    )
    # Ingest the company's full set in one call. Job "1" has a name mismatch but is
    # linked by company_id, covering the foreign-key case.
    upsert_jobs(
        [
            _job(source_job_id="1", company="Stripe Payments"),
            _job(source_job_id="2"),
            _job(source_job_id="3"),
        ],
        company_id=company.id,
    )
    jobs, _ = get_jobs()
    by_sid = {j.source_job_id: j for j in jobs}
    add_application(
        JobApplicationCreate(
            job_posting_id=by_sid["1"].id, status=JobStatusEnum.applied
        )
    )
    add_application(
        JobApplicationCreate(
            job_posting_id=by_sid["2"].id, status=JobStatusEnum.unapplied
        )
    )

    assert delete_company_by_id(company.id) is True

    remaining, _ = get_jobs()
    # "1" applied -> kept and detached; "2" unapplied and "3" untracked -> removed.
    assert {j.source_job_id for j in remaining} == {"1"}
    assert remaining[0].company_id is None

    companies, _ = get_companies(limit=10)
    assert companies == []


def test_delete_job_removes_job_and_application(clean_db):
    upsert_jobs([_job("1")])
    jobs, _ = get_jobs()
    add_application(
        JobApplicationCreate(job_posting_id=jobs[0].id, status=JobStatusEnum.applied)
    )

    assert delete_job_by_id(jobs[0].id) is True
    _, total = get_jobs()
    _, app_total = get_applications(limit=10)
    assert total == 0
    assert app_total == 0


def test_delete_application_keeps_job(clean_db):
    upsert_jobs([_job("1")])
    jobs, _ = get_jobs()
    application = add_application(
        JobApplicationCreate(job_posting_id=jobs[0].id, status=JobStatusEnum.applied)
    )

    assert delete_application_by_id(application.id) is True
    remaining, total = get_jobs()
    _, app_total = get_applications(limit=10)
    assert total == 1  # job kept
    assert remaining[0].application_status is None  # application removed
    assert app_total == 0


def test_get_stats(clean_db):
    company = add_company(
        CompanyCreate(source="greenhouse", company="Acme", board="acme")
    )
    upsert_jobs([_job(source_job_id="1"), _job(source_job_id="2")])

    stats = get_stats()
    assert stats["total_jobs"] == 2
    assert stats["total_companies"] == 1
    assert stats["last_sync"] is None  # nothing synced yet

    mark_company_synced(company.id)
    assert get_stats()["last_sync"] is not None
