"""Database access layer.

All reads and writes go through these functions. Each opens its own session and
is responsible for closing it (see the try/finally in every function).
"""

from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.db import get_session
from app.models import CompanyCreate, JobApplicationCreate, JobApplicationUpdate
from app.orm_models import (
    Company,
    JobApplication,
    JobCategoryEnum,
    JobPosting,
    JobStatusEnum,
    SectorEnum,
    SizeEnum,
)


def upsert_jobs(jobs, company_id=None):
    """Insert or update jobs, keyed on (source, source_job_id).

    Existing rows are updated in place (idempotent re-ingest); new rows are added.
    company_id links jobs to a tracked company; it is only written when supplied.

    When company_id is given, also removes that company's jobs that are no longer
    posted (see _remove_stale_jobs), so callers must pass the company's FULL current
    job set in one call.
    """
    session = get_session()
    try:
        seen_ids = set()
        for job in jobs:
            seen_ids.add(job.source_job_id)
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
                existing.category = job.category
                existing.location = job.location
                existing.currency = job.currency
                existing.salary_min = job.salary_min
                existing.salary_max = job.salary_max
                existing.is_remote = job.is_remote
                # Only overwrite the company link when a known id is supplied,
                # so the ad-hoc source endpoint doesn't wipe an existing link.
                if company_id is not None:
                    existing.company_id = company_id
            else:
                db_job = JobPosting(
                    source=job.source,
                    source_job_id=job.source_job_id,
                    company=job.company,
                    company_id=company_id,
                    title=job.title,
                    url=job.url,
                    category=job.category,
                    location=job.location,
                    currency=job.currency,
                    salary_min=job.salary_min,
                    salary_max=job.salary_max,
                    is_remote=job.is_remote,
                )
                session.add(db_job)

        # Drop jobs that vanished from the board (tracked ingests only). Skip when
        # the fetch returned nothing: an empty result is far more likely a fetch
        # failure than a genuinely empty board, and we won't wipe jobs on a hiccup.
        if company_id is not None and seen_ids:
            _remove_stale_jobs(session, company_id, seen_ids)

        session.commit()
    except IntegrityError:
        session.rollback()
        raise
    finally:
        session.close()


def _remove_stale_jobs(session, company_id, seen_ids):
    """Delete a company's jobs that are no longer posted and not worth keeping.

    A job is kept if it has an application with a status other than 'unapplied'
    (applied/rejected/offer) — you want visibility into those even after the posting
    is gone. Everything else (untracked, or tracked-but-unapplied) is deleted, along
    with any unapplied application it has. seen_ids are the source_job_ids still
    present in the latest fetch; the caller only invokes this for a non-empty fetch.
    """
    protected_ids = session.query(JobApplication.job_posting_id).filter(
        JobApplication.status != JobStatusEnum.unapplied
    )
    stale_ids = [
        row.id
        for row in session.query(JobPosting.id)
        .filter(
            JobPosting.company_id == company_id,
            JobPosting.source_job_id.notin_(seen_ids),
            ~JobPosting.id.in_(protected_ids),
        )
        .all()
    ]
    if not stale_ids:
        return

    session.query(JobApplication).filter(
        JobApplication.job_posting_id.in_(stale_ids)
    ).delete(synchronize_session=False)
    session.query(JobPosting).filter(JobPosting.id.in_(stale_ids)).delete(
        synchronize_session=False
    )


def get_stats() -> dict:
    """Summary counts and the most recent company sync time."""
    session = get_session()
    try:
        return {
            "total_jobs": session.query(func.count(JobPosting.id)).scalar(),
            "total_companies": session.query(func.count(Company.id)).scalar(),
            "last_sync": session.query(func.max(Company.last_synced_at)).scalar(),
        }
    finally:
        session.close()


def mark_company_synced(company_id) -> None:
    """Record that a company was just ingested by setting last_synced_at to now().

    Called on every successful ingest, so "last sync" advances even when no job
    data changed (unlike job.updated_at, which only moves on an actual change).
    """
    session = get_session()
    try:
        session.query(Company).filter(Company.id == company_id).update(
            {Company.last_synced_at: func.now()}, synchronize_session=False
        )
        session.commit()
    finally:
        session.close()


def get_jobs(
    company: str | None = None,
    limit: int = 25,
    offset: int = 0,
    tracked: bool | None = None,
    application_status: JobStatusEnum | None = None,
    size: SizeEnum | None = None,
    sector: SectorEnum | None = None,
    category: JobCategoryEnum | None = None,
    location: str | None = None,
    is_remote: bool | None = None,
) -> tuple[list[JobPosting], int]:
    """Return a page of jobs matching the given filters, plus the total match count.

    Returns (items, total) where total ignores limit/offset so callers can paginate.
    """
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    session = get_session()
    try:
        # Eager-load the application so JobPosting.application_status is populated
        # before the session closes (avoids a detached-instance lazy load).
        q = session.query(JobPosting).options(joinedload(JobPosting.application))
        if company:
            q = q.filter(JobPosting.company == company)

        if category is not None:
            q = q.filter(JobPosting.category == category)

        # Case-insensitive substring match, so "york" matches "New York, NY".
        if location:
            q = q.filter(JobPosting.location.ilike(f"%{location}%"))

        if is_remote is not None:
            q = q.filter(JobPosting.is_remote == is_remote)

        # size/sector live on the linked company, so join via the company_id FK.
        if size is not None or sector is not None:
            q = q.join(Company, JobPosting.company_id == Company.id)
            if size is not None:
                q = q.filter(Company.size == size)
            if sector is not None:
                q = q.filter(Company.sector == sector)

        # tracked True/False selects jobs that do / do not have an application.
        if tracked is not None:
            application_ids = session.query(JobApplication.job_posting_id)
            if tracked:
                q = q.filter(JobPosting.id.in_(application_ids))
            else:
                q = q.filter(~JobPosting.id.in_(application_ids))

        if application_status is not None:
            status_ids = session.query(JobApplication.job_posting_id).filter(
                JobApplication.status == application_status
            )
            q = q.filter(JobPosting.id.in_(status_ids))

        # total counts the whole filtered set; the page then applies limit/offset.
        total = q.count()
        items = q.order_by(JobPosting.id.desc()).limit(limit).offset(offset).all()
        return items, total
    finally:
        session.close()


def get_job(db_id: int) -> JobPosting | None:
    """Return a single job by primary key, or None if it does not exist."""
    session = get_session()
    try:
        q = session.query(JobPosting).options(joinedload(JobPosting.application))
        q = q.filter(JobPosting.id == db_id)
        return q.one_or_none()
    finally:
        session.close()


def add_company(company_in: CompanyCreate) -> Company | None:
    """Create a tracked company, or return None if (source, company, board) exists."""
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


def get_companies(limit: int, offset: int = 0) -> tuple[list[Company], int]:
    """Return a page of Company rows (alphabetical) and the total count.

    Limit is clamped between 1 and 500; offset is clamped to >= 0.
    """
    session = get_session()
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    try:
        q = session.query(Company)
        total = q.count()
        items = q.order_by(Company.company.asc()).limit(limit).offset(offset).all()
        return items, total
    finally:
        session.close()


def delete_company_by_id(db_id: int) -> bool:
    """Delete a company, keeping jobs whose applications are worth keeping.

    Jobs with an application status other than 'unapplied' (applied/rejected/offer)
    are kept for visibility and detached from the company (company_id set to NULL).
    Every other job for the company — untracked or tracked-but-unapplied — is deleted
    along with any unapplied application.

    Returns True if the company existed and was deleted, else False.
    """
    session = get_session()
    try:
        company = session.query(Company).filter(Company.id == db_id).one_or_none()

        if company is None:
            return False

        # Match postings linked by the company_id FK OR by the legacy (company, source)
        # strings, so a name mismatch can't leave an orphan referencing this company.
        posting_filter = or_(
            JobPosting.company_id == company.id,
            and_(
                JobPosting.company == company.company,
                JobPosting.source == company.source,
            ),
        )
        # Jobs protected by a meaningful application (any status but 'unapplied').
        protected_ids = session.query(JobApplication.job_posting_id).filter(
            JobApplication.status != JobStatusEnum.unapplied
        )

        removable_ids = [
            row.id
            for row in session.query(JobPosting.id)
            .filter(posting_filter, ~JobPosting.id.in_(protected_ids))
            .all()
        ]
        # Delete removable jobs and any unapplied application they have.
        session.query(JobApplication).filter(
            JobApplication.job_posting_id.in_(removable_ids)
        ).delete(synchronize_session=False)
        session.query(JobPosting).filter(JobPosting.id.in_(removable_ids)).delete(
            synchronize_session=False
        )

        # Detach kept jobs so the company FK doesn't block deletion; the company
        # name stays on the job row for context.
        session.query(JobPosting).filter(
            posting_filter, JobPosting.id.in_(protected_ids)
        ).update({JobPosting.company_id: None}, synchronize_session=False)

        session.delete(company)
        session.commit()
        return True

    finally:
        session.close()


def delete_job_by_id(db_id: int) -> bool:
    """Delete a single job and its application, if any. False if it does not exist."""
    session = get_session()
    try:
        job = session.query(JobPosting).filter(JobPosting.id == db_id).one_or_none()
        if job is None:
            return False
        session.query(JobApplication).filter(
            JobApplication.job_posting_id == db_id
        ).delete(synchronize_session=False)
        session.delete(job)
        session.commit()
        return True
    finally:
        session.close()


def delete_application_by_id(application_id: int) -> bool:
    """Delete a single application; the job is kept. False if it does not exist."""
    session = get_session()
    try:
        app_row = (
            session.query(JobApplication)
            .filter(JobApplication.id == application_id)
            .one_or_none()
        )
        if app_row is None:
            return False
        session.delete(app_row)
        session.commit()
        return True
    finally:
        session.close()


def add_application(app_in: JobApplicationCreate) -> JobApplication | None | str:
    """Create job application.

    Returns:
        JobApplication: if created successfully
        None: if the referenced job does not exist
        "duplicate": if an application already exists for the job
    """
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
    limit: int, status: JobStatusEnum | None = None, offset: int = 0
) -> tuple[list[JobApplication], int]:
    """Return a page of applications (optionally filtered by status) and the total.

    Returns (items, total) where total ignores limit/offset so callers can paginate.
    """
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    session = get_session()

    try:
        # Eager-load the job AND the job's application back-reference: the nested
        # JobOut exposes application_status, which would otherwise lazy-load the
        # relationship after the session is closed (DetachedInstanceError).
        query = session.query(JobApplication).options(
            joinedload(JobApplication.job).joinedload(JobPosting.application)
        )

        if status is not None:
            query = query.filter(JobApplication.status == status)

        total = query.count()
        items = (
            query.order_by(JobApplication.updated_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        return items, total

    finally:
        session.close()


def update_application(
    application_id: int, app_update: JobApplicationUpdate
) -> JobApplication | None:
    """Update the application's set fields by id; return it, or None if not found."""
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
