"""add documents table

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("research_projects.id"), nullable=True),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("collection", sa.String(128), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "indexing", "indexed", "failed", name="document_status", create_constraint=True),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("chunk_count", sa.Integer, nullable=True),
        sa.Column("char_count", sa.Integer, nullable=True),
        sa.Column("author", sa.String(256), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("documents")
    op.execute("DROP TYPE IF EXISTS document_status")
