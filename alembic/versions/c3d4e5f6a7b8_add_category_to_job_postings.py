"""add category to job_postings

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-09 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


job_category = sa.Enum(
    "software_engineering",
    "data",
    "product",
    "design",
    "sales",
    "marketing",
    "finance",
    "operations",
    "people",
    "other",
    name="jobcategoryenum",
)


def upgrade() -> None:
    """Add a nullable job-function category to postings.

    Existing rows stay NULL until the next ingest recategorizes them.
    """
    job_category.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "job_postings",
        sa.Column("category", job_category, nullable=True),
    )


def downgrade() -> None:
    """Drop the category column and its enum type."""
    op.drop_column("job_postings", "category")
    job_category.drop(op.get_bind(), checkfirst=True)
