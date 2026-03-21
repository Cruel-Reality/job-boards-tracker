"""align existing schema with ORM models

Revision ID: abb82e52d398
Revises: 3019aeba48d4
Create Date: 2026-03-20 22:18:46.589832
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "abb82e52d398"
down_revision: Union[str, Sequence[str], None] = "3019aeba48d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


sector_enum = postgresql.ENUM(
    "pharma",
    "tech",
    "cybersecurity",
    "finance",
    "robotics",
    "healthcare",
    name="sectorenum",
)

size_enum = postgresql.ENUM(
    "startup",
    "small",
    "medium",
    "big",
    name="sizeenum",
)


def upgrade() -> None:
    """Upgrade schema."""
    sector_enum.create(op.get_bind(), checkfirst=True)
    size_enum.create(op.get_bind(), checkfirst=True)

    op.execute(
        "ALTER TABLE company_sources "
        "ALTER COLUMN sector TYPE sectorenum "
        "USING sector::sectorenum"
    )
    op.execute(
        "ALTER TABLE company_sources "
        "ALTER COLUMN size TYPE sizeenum "
        "USING size::sizeenum"
    )

    op.alter_column(
        "company_sources",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    op.alter_column(
        "company_sources",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(),
        nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    op.create_unique_constraint(
        "uq_company_source_board",
        "company_sources",
        ["source", "company", "board"],
    )
    op.alter_column(
        "job_postings",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "job_postings",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "job_postings",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "job_postings",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_constraint("uq_company_source_board", "company_sources", type_="unique")
    op.alter_column(
        "company_sources",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(),
        nullable=True,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    op.alter_column(
        "company_sources",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        nullable=True,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )

    op.execute(
        "ALTER TABLE company_sources ALTER COLUMN size TYPE VARCHAR USING size::text"
    )
    op.execute(
        "ALTER TABLE company_sources "
        "ALTER COLUMN sector TYPE VARCHAR "
        "USING sector::text"
    )

    size_enum.drop(op.get_bind(), checkfirst=True)
    sector_enum.drop(op.get_bind(), checkfirst=True)
