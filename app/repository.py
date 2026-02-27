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
