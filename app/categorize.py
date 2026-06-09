"""Map a job title to a coarse job-function category.

A small ordered keyword matcher: the first category with a keyword found in the
lowercased title wins, so order encodes precedence. More specific buckets come
before generic ones, e.g. "data engineer" resolves to data, not the catch-all
"engineer" in software_engineering. Falls back to other when nothing matches.
"""

from app.orm_models import JobCategoryEnum

# Ordered (category, keywords). First keyword hit, top to bottom, decides.
_CATEGORY_KEYWORDS: list[tuple[JobCategoryEnum, tuple[str, ...]]] = [
    (
        JobCategoryEnum.data,
        (
            "data engineer",
            "data scientist",
            "data analyst",
            "data science",
            "machine learning",
            "ml engineer",
            "ai engineer",
            "analytics",
            "data platform",
            "bioinformatics",
        ),
    ),
    (
        JobCategoryEnum.product,
        ("product manager", "product owner", "head of product", "product lead"),
    ),
    (
        JobCategoryEnum.design,
        ("designer", "ux", "user experience", "user research", "creative director"),
    ),
    (
        JobCategoryEnum.sales,
        (
            "sales",
            "account executive",
            "account manager",
            "business development",
            "partnerships",
            "solutions engineer",
        ),
    ),
    (
        JobCategoryEnum.marketing,
        (
            "marketing",
            "growth",
            "seo",
            "content",
            "brand",
            "communications",
            "social media",
            "demand generation",
        ),
    ),
    (
        JobCategoryEnum.finance,
        (
            "finance",
            "financial",
            "accountant",
            "accounting",
            "controller",
            "fp&a",
            "treasury",
            "auditor",
            "bookkeep",
            "payroll",
        ),
    ),
    (
        JobCategoryEnum.people,
        (
            "recruit",
            "talent",
            "human resources",
            "people operations",
            "people ops",
            "hiring",
        ),
    ),
    (
        JobCategoryEnum.operations,
        (
            "operations",
            "program manager",
            "project manager",
            "supply chain",
            "logistics",
            "office manager",
            "chief of staff",
        ),
    ),
    (
        JobCategoryEnum.software_engineering,
        (
            "software engineer",
            "software developer",
            "swe",
            "backend",
            "back end",
            "back-end",
            "frontend",
            "front end",
            "front-end",
            "full stack",
            "fullstack",
            "full-stack",
            "developer",
            "devops",
            "site reliability",
            "platform engineer",
            "mobile engineer",
            "security engineer",
            "infrastructure",
            "qa engineer",
            "test engineer",
            "engineer",
            "engineering",
            "programmer",
            "architect",
        ),
    ),
]


def categorize_title(title: str) -> JobCategoryEnum:
    """Return the best-guess job-function category for a title."""
    text = title.lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return category
    return JobCategoryEnum.other
