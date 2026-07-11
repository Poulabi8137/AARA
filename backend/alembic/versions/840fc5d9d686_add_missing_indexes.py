"""add_missing_indexes

Revision ID: 840fc5d9d686
Revises: 840fc5d9d685
Create Date: 2026-07-01 00:00:00.000000

"""
from __future__ import annotations

from alembic import op

revision = "840fc5d9d686"
down_revision = "840fc5d9d685"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Hot-path lookups (WorkspaceRepository.get_by_owner / get_for_user) filter
    # by owner_id and by workspace_members.user_id; neither had an index.
    op.create_index("ix_workspaces_owner_id", "workspaces", ["owner_id"])
    op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"])

    # Duplicate-detection lookups filter by (workspace_id, content_hash); enforce
    # uniqueness at the DB level too, scoped per-workspace (same content hash can
    # legitimately exist in two different workspaces).
    op.create_index(
        "uq_research_papers_workspace_id_content_hash",
        "research_papers",
        ["workspace_id", "content_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_research_papers_workspace_id_content_hash", table_name="research_papers")
    op.drop_index("ix_workspace_members_user_id", table_name="workspace_members")
    op.drop_index("ix_workspaces_owner_id", table_name="workspaces")
