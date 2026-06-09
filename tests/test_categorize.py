"""Tests for title-to-category classification."""

import pytest

from app.categorize import categorize_title
from app.orm_models import JobCategoryEnum


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Senior Software Engineer", JobCategoryEnum.software_engineering),
        ("Backend Developer", JobCategoryEnum.software_engineering),
        ("Full Stack Engineer", JobCategoryEnum.software_engineering),
        ("Site Reliability Engineer", JobCategoryEnum.software_engineering),
        # Data wins over the generic "engineer" keyword.
        ("Data Engineer", JobCategoryEnum.data),
        ("Senior Data Scientist", JobCategoryEnum.data),
        ("Machine Learning Engineer", JobCategoryEnum.data),
        ("Product Manager", JobCategoryEnum.product),
        ("Senior Product Designer", JobCategoryEnum.design),
        ("UX Researcher", JobCategoryEnum.design),
        ("Account Executive", JobCategoryEnum.sales),
        ("Sales Engineer", JobCategoryEnum.sales),
        ("Growth Marketing Lead", JobCategoryEnum.marketing),
        ("Staff Accountant", JobCategoryEnum.finance),
        ("Senior Financial Analyst", JobCategoryEnum.finance),
        ("Technical Recruiter", JobCategoryEnum.people),
        ("Program Manager", JobCategoryEnum.operations),
        ("Chief of Staff", JobCategoryEnum.operations),
        ("Veterinarian", JobCategoryEnum.other),
    ],
)
def test_categorize_title(title, expected):
    assert categorize_title(title) == expected


def test_categorize_is_case_insensitive():
    assert categorize_title("SOFTWARE ENGINEER") == JobCategoryEnum.software_engineering
    assert categorize_title("data scientist") == JobCategoryEnum.data
