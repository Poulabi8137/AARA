"""add_hashed_password_to_users

Revision ID: 840fc5d9d683
Revises: 840fc5d9d682
Create Date: 2026-06-29 00:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "840fc5d9d683"
down_revision = "840fc5d9d682"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add hashed_password column if it does not already exist (idempotent via try/except)
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("hashed_password", sa.String(255), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("hashed_password")
