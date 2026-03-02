from sqlalchemy.exc import IntegrityError

from app.db import get_session
from app.models import CompanyCreate
from app.orm_models import Company, JobPosting


def upsert_job(job):
    session = get_session()
    try:
        existing = (
            session.query(JobPosting)
            .filter(
                JobPosting.source == job.source,
                JobPosting.source_job_id == job.source_job_id,
            )
            .one_or_none()
        )
        if existing:
            existing.company = job.company
            existing.title = job.title
            existing.url = job.url
            existing.location = job.location
            existing.currency = job.currency
            existing.salary_min = job.salary_min
            existing.salary_max = job.salary_max
            existing.is_remote = job.is_remote
        else:
            db_job = JobPosting(
                source=job.source,
                source_job_id=job.source_job_id,
                company=job.company,
                title=job.title,
                url=job.url,
                location=job.location,
                currency=job.currency,
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                is_remote=job.is_remote,
            )
            session.add(db_job)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise
    finally:
        session.close()


def get_jobs(company: str | None = None, limit: int = 25) -> list[JobPosting]:
    limit = max(1, min(limit, 100))
    session = get_session()
    try:
        q = session.query(JobPosting)
        if company:
            q = q.filter(JobPosting.company == company)
        return q.order_by(JobPosting.id.desc()).limit(limit).all()
    finally:
        session.close()


def get_job(db_id: int) -> JobPosting | None:
    session = get_session()
    try:
        q = session.query(JobPosting)
        q = q.filter(JobPosting.id == db_id)
        return q.one_or_none()
    finally:
        session.close()


def add_company(company_in: CompanyCreate) -> Company | None:
    session = get_session()
    try:
        db_company = Company(
            source=company_in.source,
            company=company_in.company,
            board=company_in.board,
            sector=company_in.sector,
            size=company_in.size,
        )
        session.add(db_company)
        session.commit()
        session.refresh(db_company)
        return db_company
    except IntegrityError:
        session.rollback()
        return None
    finally:
        session.close()


def get_company_by_company_and_source_and_board(
    company: str, source: str, board: str
) -> Company | None:
    session = get_session()
    try:
        q = session.query(Company)
        q = q.filter(
            Company.company == company, Company.source == source, Company.board == board
        )
        return q.one_or_none()
    finally:
        session.close()
