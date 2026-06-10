"""Tests for source-agnostic field derivation helpers."""

import pytest

from app.normalize import build_job, infer_remote
from app.orm_models import JobCategoryEnum, SeniorityEnum


@pytest.mark.parametrize(
    "location,expected",
    [
        ("Remote", True),
        ("Remote - US", True),
        ("remote (anywhere)", True),
        ("New York, NY", False),
        ("San Francisco, CA", False),
        (None, True),
        ("", True),
    ],
)
def test_infer_remote(location, expected):
    assert infer_remote(location) is expected


def test_build_job_applies_derivations():
    job = build_job(
        source="greenhouse",
        source_job_id="1",
        company="Acme",
        title="Senior Data Engineer",
        url="https://example.com/1",
        location="Remote",
    )
    assert job.category == JobCategoryEnum.data
    assert job.seniority == SeniorityEnum.senior
    assert job.is_remote is True
