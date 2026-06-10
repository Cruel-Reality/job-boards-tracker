"""convert timestamp columns to timezone-aware

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-09 13:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, column) for every timestamp column. Existing naive values are UTC.
_COLUMNS = [
    ("job_postings", "created_at"),
    ("job_postings", "updated_at"),
    ("company_sources", "created_at"),
    ("company_sources", "updated_at"),
    ("company_sources", "last_synced_at"),
    ("job_applications", "created_at"),
    ("job_applications", "updated_at"),
    ("job_applications", "applied_at"),
]


def upgrade() -> None:
    """Convert naive timestamp columns to timestamptz, reading them as UTC."""
    for table, col in _COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {col} "
            f"TYPE timestamptz USING {col} AT TIME ZONE 'UTC'"
        )


def downgrade() -> None:
    """Convert back to naive timestamps expressed in UTC."""
    for table, col in _COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {col} "
            f"TYPE timestamp USING {col} AT TIME ZONE 'UTC'"
        )
