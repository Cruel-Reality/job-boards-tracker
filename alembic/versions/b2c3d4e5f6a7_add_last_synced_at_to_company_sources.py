"""add last_synced_at to company_sources

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-08 11:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add a nullable last_synced_at timestamp to tracked companies."""
    op.add_column(
        "company_sources",
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """Drop the last_synced_at column."""
    op.drop_column("company_sources", "last_synced_at")
