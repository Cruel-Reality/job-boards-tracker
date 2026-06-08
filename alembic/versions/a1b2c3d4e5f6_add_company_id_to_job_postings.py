"""add company_id foreign key to job_postings

Revision ID: a1b2c3d4e5f6
Revises: 790364e7ed07
Create Date: 2026-06-08 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "790364e7ed07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable company_id FK and backfill existing rows."""
    op.add_column("job_postings", sa.Column("company_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_job_postings_company_id",
        "job_postings",
        "company_sources",
        ["company_id"],
        ["id"],
    )
    # Best-effort backfill for pre-existing rows by matching on (company, source).
    # Going forward ingestion sets company_id directly, so this string match only
    # affects historical data; rows with no matching company keep company_id = NULL.
    op.execute(
        """
        UPDATE job_postings AS j
        SET company_id = c.id
        FROM company_sources AS c
        WHERE c.company = j.company AND c.source = j.source
        """
    )


def downgrade() -> None:
    """Drop the company_id FK and column."""
    op.drop_constraint(
        "fk_job_postings_company_id", "job_postings", type_="foreignkey"
    )
    op.drop_column("job_postings", "company_id")
