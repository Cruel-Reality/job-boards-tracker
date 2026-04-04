from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.db import get_session
from app.models import CompanyCreate, JobApplicationCreate, JobApplicationUpdate
from app.orm_models import Company, JobApplication, JobPosting, JobStatusEnum


def upsert_jobs(jobs):
    session = get_session()
    try:
        for job in jobs:
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


def get_companies(limit: int) -> list[Company]:
    session = get_session()
    limit = max(1, min(limit, 500))
    try:
        q = session.query(Company)
        return q.order_by(Company.company.asc()).limit(limit).all()
    finally:
        session.close()


def delete_company_by_id(db_id: int) -> bool:
    session = get_session()
    try:
        company = session.query(Company).filter(Company.id == db_id).one_or_none()

        if company is None:
            return False

        # get IDs of postings being deleted, then delete their applications first
        posting_ids = [
            row.id
            for row in session.query(JobPosting.id)
            .filter(
                JobPosting.company == company.company,
                JobPosting.source == company.source,
            )
            .all()
        ]

        session.query(JobApplication).filter(
            JobApplication.job_posting_id.in_(posting_ids)
        ).delete(synchronize_session=False)

        session.query(JobPosting).filter(
            JobPosting.company == company.company, JobPosting.source == company.source
        ).delete()

        session.delete(company)
        session.commit()
        return True

    finally:
        session.close()


def add_application(app_in: JobApplicationCreate) -> JobApplication | None | str:
    session = get_session()
    try:
        job = (
            session.query(JobPosting)
            .filter(JobPosting.id == app_in.job_posting_id)
            .one_or_none()
        )

        if job is None:
            return None

        db_app = JobApplication(
            job_posting_id=app_in.job_posting_id,
            status=app_in.status,
            notes=app_in.notes,
            applied_at=app_in.applied_at,
        )

        session.add(db_app)
        session.commit()
        session.refresh(db_app)
        return db_app

    except IntegrityError:
        session.rollback()
        return "duplicate"

    finally:
        session.close()


def get_applications(
    limit: int, status: JobStatusEnum | None = None
) -> list[JobApplication]:
    limit = max(1, min(limit, 500))
    session = get_session()

    try:
        query = session.query(JobApplication).options(joinedload(JobApplication.job))

        if status is not None:
            query = query.filter(JobApplication.status == status)

        return query.order_by(JobApplication.updated_at.desc()).limit(limit).all()

    finally:
        session.close()


def update_application(
    application_id: int, app_update: JobApplicationUpdate
) -> JobApplication | None:
    session = get_session()

    try:
        db_app = (
            session.query(JobApplication)
            .filter(JobApplication.id == application_id)
            .one_or_none()
        )

        if db_app is None:
            return None

        update_data = app_update.model_dump(exclude_unset=True)

        for field, val in update_data.items():
            setattr(db_app, field, val)

        session.commit()
        session.refresh(db_app)
        return db_app

    finally:
        session.close()
