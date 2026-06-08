import os

# Point the app at a disposable TEST database before any app module is imported,
# so db.py binds its engine to the test DB and never the dev/prod DATABASE_URL.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://job_user:devpassword@localhost:5432/job_tracker_test",
)

import pytest  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

from app.db import Base, engine, get_session  # noqa: E402
from app.orm_models import Company, JobApplication, JobPosting  # noqa: E402


@pytest.fixture(scope="session")
def _db_schema():
    """Create the schema on the test database for DB-backed tests.

    Locally, skip these tests when no database is reachable. In CI (CI=true) a
    missing database is a hard failure instead of a silent skip, so green CI
    really means the data layer was exercised.
    """
    try:
        engine.connect().close()
    except OperationalError:
        if os.environ.get("CI"):
            raise
        pytest.skip("No test database reachable")
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


def _truncate():
    """Empty all tables, respecting foreign-key order."""
    session = get_session()
    try:
        session.query(JobApplication).delete()
        session.query(JobPosting).delete()
        session.query(Company).delete()
        session.commit()
    finally:
        session.close()


@pytest.fixture
def clean_db(_db_schema):
    """Provide an empty test database around each DB-backed test."""
    _truncate()
    yield
    _truncate()
