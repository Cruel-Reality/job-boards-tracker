from app.models import CompanyCreate, JobApplicationCreate, JobBase
from app.orm_models import JobStatusEnum, SectorEnum, SizeEnum
from app.repository import (
    add_application,
    add_company,
    delete_company_by_id,
    get_companies,
    get_jobs,
    get_stats,
    upsert_jobs,
)


def _job(source_job_id="1", company="Acme", title="Engineer"):
    return JobBase(
        source="greenhouse",
        source_job_id=source_job_id,
        company=company,
        title=title,
        url=f"https://example.com/{source_job_id}",
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


def test_delete_company_handles_name_mismatch_without_fk_error(clean_db):
    # Company tracked as "Stripe", but the ingested job's company string differs
    # while still linked by company_id. The old string-only delete would miss this
    # job and raise a foreign-key violation when deleting the company.
    company = add_company(
        CompanyCreate(source="greenhouse", company="Stripe", board="stripe")
    )
    upsert_jobs(
        [_job(source_job_id="1", company="Stripe Payments")], company_id=company.id
    )
    jobs, _ = get_jobs()
    add_application(
        JobApplicationCreate(job_posting_id=jobs[0].id, status=JobStatusEnum.applied)
    )

    assert delete_company_by_id(company.id) is True
    remaining_jobs, _ = get_jobs()
    remaining_companies, _ = get_companies(limit=10)
    assert remaining_jobs == []
    assert remaining_companies == []


def test_get_stats(clean_db):
    add_company(CompanyCreate(source="greenhouse", company="Acme", board="acme"))
    upsert_jobs([_job(source_job_id="1"), _job(source_job_id="2")])

    stats = get_stats()
    assert stats["total_jobs"] == 2
    assert stats["total_companies"] == 1
    assert stats["last_job_update"] is not None
