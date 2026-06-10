"""Source-agnostic helpers for building normalized jobs.

build_job is the single place every source turns its raw fields into a JobBase,
so the derived fields (category, seniority, remote) are computed consistently and
a new source can't forget one. See also app.categorize and app.seniority.
"""

from app.categorize import categorize_title
from app.models import JobBase
from app.seniority import classify_seniority


def infer_remote(location: str | None) -> bool:
    """Best-guess remote flag from a location string.

    A "remote" mention counts as remote, and a posting with no location is assumed
    remote (nothing tying it to a physical office).
    """
    if not location:
        return True
    return "remote" in location.lower()


def build_job(
    *,
    source: str,
    source_job_id: str,
    company: str,
    title: str,
    url: str,
    location: str | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    currency: str | None = None,
) -> JobBase:
    """Build a normalized JobBase, deriving category, seniority, and remote.

    Sources supply raw fields only; the derivations live here so every source
    stays consistent. Keyword-only to keep call sites self-documenting.
    """
    return JobBase(
        source=source,
        source_job_id=source_job_id,
        company=company,
        title=title,
        url=url,
        category=categorize_title(title),
        seniority=classify_seniority(title),
        location=location,
        salary_min=salary_min,
        salary_max=salary_max,
        currency=currency,
        is_remote=infer_remote(location),
    )
