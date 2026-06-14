"""extend agent_executions with tracking fields

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agent_executions", sa.Column("input_query", sa.Text, nullable=True))
    op.add_column("agent_executions", sa.Column("output_report", sa.Text, nullable=True))
    op.add_column("agent_executions", sa.Column("thread_id", sa.String(128), nullable=True))
    op.add_column("agent_executions", sa.Column("token_usage", JSON, nullable=True))
    op.add_column("agent_executions", sa.Column("node_durations", JSON, nullable=True))
    op.add_column("agent_executions", sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"))
    op.add_column("agent_executions", sa.Column("error_message", sa.Text, nullable=True))
    op.add_column("agent_executions", sa.Column("execution_metadata", JSON, nullable=True))

    op.execute("ALTER TYPE execution_status ADD VALUE IF NOT EXISTS 'cancelled'")


def downgrade() -> None:
    op.drop_column("agent_executions", "input_query")
    op.drop_column("agent_executions", "output_report")
    op.drop_column("agent_executions", "thread_id")
    op.drop_column("agent_executions", "token_usage")
    op.drop_column("agent_executions", "node_durations")
    op.drop_column("agent_executions", "retry_count")
    op.drop_column("agent_executions", "error_message")
    op.drop_column("agent_executions", "execution_metadata")
