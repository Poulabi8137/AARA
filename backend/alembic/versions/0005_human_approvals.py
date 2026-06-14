"""create human_approvals table

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "human_approvals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("execution_id", UUID(as_uuid=True), sa.ForeignKey("agent_executions.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(256), nullable=True),
        sa.Column("feedback", sa.Text, nullable=True),
    )
    op.create_index("ix_human_approvals_execution_id", "human_approvals", ["execution_id"])
    op.create_index("ix_human_approvals_status", "human_approvals", ["status"])


def downgrade() -> None:
    op.drop_table("human_approvals")
