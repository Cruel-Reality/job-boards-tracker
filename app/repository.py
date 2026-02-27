from sqlalchemy.exc import IntegrityError

from app.db import get_session
from app.orm_models import JobPosting


def upsert_job(job):
    session = get_session()
    try:
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
        return q.first()
    finally:
        session.close()
