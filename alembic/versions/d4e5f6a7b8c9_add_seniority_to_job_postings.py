"""add seniority to job_postings

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-09 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


seniority = sa.Enum(
    "intern",
    "entry",
    "mid",
    "senior",
    "staff",
    "lead",
    "manager",
    "director",
    "executive",
    name="seniorityenum",
)


def upgrade() -> None:
    """Add a nullable seniority bucket to postings.

    Existing rows stay NULL until the next ingest reclassifies them.
    """
    seniority.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "job_postings",
        sa.Column("seniority", seniority, nullable=True),
    )


def downgrade() -> None:
    """Drop the seniority column and its enum type."""
    op.drop_column("job_postings", "seniority")
    seniority.drop(op.get_bind(), checkfirst=True)
