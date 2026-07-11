"""add_session_results

Revision ID: 840fc5d9d687
Revises: 840fc5d9d686
Create Date: 2026-07-02 00:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "840fc5d9d687"
down_revision = "840fc5d9d686"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Agent phase output (analysis gaps/themes, idea generation, etc.) was
    # computed and then discarded — trigger_analysis/trigger_writing only
    # ever returned session metadata. This column lets research_service.py
    # persist each phase's AgentOutput so it can be read back by the API
    # instead of silently vanishing after execute() returns.
    op.add_column(
        "research_sessions",
        sa.Column("results", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("research_sessions", "results")
