"""Tests for title-to-seniority classification."""

import pytest

from app.orm_models import SeniorityEnum
from app.seniority import classify_seniority


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Software Engineering Intern", SeniorityEnum.intern),
        ("Chief Technology Officer", SeniorityEnum.executive),
        ("VP of Engineering", SeniorityEnum.director),
        ("Director of Data", SeniorityEnum.director),
        ("Engineering Manager", SeniorityEnum.manager),
        # Management keyword wins over the senior modifier.
        ("Senior Engineering Manager", SeniorityEnum.manager),
        ("Engineering Team Lead", SeniorityEnum.lead),
        ("Staff Software Engineer", SeniorityEnum.staff),
        ("Principal Engineer", SeniorityEnum.staff),
        ("Senior Software Engineer", SeniorityEnum.senior),
        ("Software Engineer II", SeniorityEnum.mid),
        ("Junior Developer", SeniorityEnum.entry),
        ("Associate Software Engineer", SeniorityEnum.entry),
        # No seniority signal -> None.
        ("Software Engineer", None),
        ("Data Scientist", None),
    ],
)
def test_classify_seniority(title, expected):
    assert classify_seniority(title) == expected


def test_classify_seniority_is_case_insensitive():
    assert classify_seniority("SENIOR SOFTWARE ENGINEER") == SeniorityEnum.senior
    assert classify_seniority("staff engineer") == SeniorityEnum.staff
