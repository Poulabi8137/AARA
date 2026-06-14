"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("email", sa.String(320), unique=True, nullable=False, index=True),
        sa.Column("password_hash", sa.String(128), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "researcher", "viewer", name="user_role", create_constraint=True),
            nullable=False,
            server_default="researcher",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "research_projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.Enum("draft", "active", "completed", "archived", name="project_status", create_constraint=True),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "research_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("research_projects.id"), nullable=False),
        sa.Column("session_name", sa.String(256), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "completed", "failed", name="session_status", create_constraint=True),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "research_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("research_projects.id"), nullable=False),
        sa.Column(
            "report_type",
            sa.Enum("academic", "executive", "comprehensive", name="report_type", create_constraint=True),
            nullable=False,
            server_default="academic",
        ),
        sa.Column("report_path", sa.String(1024), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "agent_executions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("research_projects.id"), nullable=False),
        sa.Column("agent_name", sa.String(256), nullable=False),
        sa.Column(
            "execution_status",
            sa.Enum("pending", "running", "completed", "failed", name="execution_status", create_constraint=True),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_log", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("agent_executions")
    op.drop_table("research_reports")
    op.drop_table("research_sessions")
    op.drop_table("research_projects")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP TYPE IF EXISTS project_status")
    op.execute("DROP TYPE IF EXISTS session_status")
    op.execute("DROP TYPE IF EXISTS report_type")
    op.execute("DROP TYPE IF EXISTS execution_status")
