"""Add Research Memory models (UserResearchProfile, SessionMemory, etc.)

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-20
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_user_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("expertise_areas", postgresql.JSON, nullable=True),
        sa.Column("research_interests", postgresql.JSON, nullable=True),
        sa.Column("preferred_methodologies", postgresql.JSON, nullable=True),
        sa.Column("domains", postgresql.JSON, nullable=True),
        sa.Column("skill_level", sa.String(64), nullable=True),
        sa.Column("preferences", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_research_user_profiles_user_id", "research_user_profiles", ["user_id"])

    op.create_table(
        "session_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_sessions.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("memory_type", sa.Enum("conversation", "finding", "observation", "insight", "query", "agent_output", "decision", name="session_memory_type", create_constraint=True), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("source", sa.Enum("agent", "user", "paper", "system", "external", name="memory_source", create_constraint=True), nullable=False),
        sa.Column("importance", sa.Enum("low", "medium", "high", "critical", name="memory_importance", create_constraint=True), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("memory_metadata", postgresql.JSON, nullable=True),
        sa.Column("embedding_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_session_memories_session_id", "session_memories", ["session_id"])
    op.create_index("ix_session_memories_user_id", "session_memories", ["user_id"])
    op.create_index("ix_session_memories_embedding_id", "session_memories", ["embedding_id"])

    op.create_table(
        "long_term_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("category", sa.Enum("research_pattern", "methodology_preference", "domain_knowledge", "user_preference", "cross_session_insight", "reusable_finding", name="long_term_memory_category", create_constraint=True), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("source_session_ids", postgresql.JSON, nullable=True),
        sa.Column("importance", sa.Enum("low", "medium", "high", "critical", name="long_term_memory_importance", create_constraint=True), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("memory_metadata", postgresql.JSON, nullable=True),
        sa.Column("embedding_id", sa.String(128), nullable=True),
        sa.Column("consolidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_long_term_memories_user_id", "long_term_memories", ["user_id"])
    op.create_index("ix_long_term_memories_embedding_id", "long_term_memories", ["embedding_id"])

    op.create_table(
        "paper_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_projects.id"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("memory_type", sa.Enum("key_finding", "methodology", "limitation", "citation_insight", "future_work", "dataset_note", "experiment_note", name="paper_memory_type", create_constraint=True), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("source_paper_title", sa.String(512), nullable=True),
        sa.Column("source_doi", sa.String(1024), nullable=True),
        sa.Column("relevance_score", sa.Float, nullable=False),
        sa.Column("memory_metadata", postgresql.JSON, nullable=True),
        sa.Column("embedding_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_paper_memories_project_id", "paper_memories", ["project_id"])
    op.create_index("ix_paper_memories_document_id", "paper_memories", ["document_id"])
    op.create_index("ix_paper_memories_user_id", "paper_memories", ["user_id"])
    op.create_index("ix_paper_memories_embedding_id", "paper_memories", ["embedding_id"])

    op.create_table(
        "project_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_projects.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("category", sa.Enum("research_direction", "methodology_decision", "aggregated_insight", "experiment_result", "hypothesis", "knowledge_gap", name="project_memory_category", create_constraint=True), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("importance", sa.Enum("low", "medium", "high", "critical", name="project_memory_importance", create_constraint=True), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("memory_metadata", postgresql.JSON, nullable=True),
        sa.Column("embedding_id", sa.String(128), nullable=True),
        sa.Column("source_memory_ids", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_project_memories_project_id", "project_memories", ["project_id"])
    op.create_index("ix_project_memories_user_id", "project_memories", ["user_id"])
    op.create_index("ix_project_memories_embedding_id", "project_memories", ["embedding_id"])

    op.create_table(
        "semantic_memory_indices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("memory_type", sa.String(64), nullable=False),
        sa.Column("memory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("embedding_id", sa.String(128), nullable=False),
        sa.Column("collection_name", sa.String(128), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=True),
        sa.Column("memory_metadata", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_semantic_memory_indices_memory_type", "semantic_memory_indices", ["memory_type"])
    op.create_index("ix_semantic_memory_indices_memory_id", "semantic_memory_indices", ["memory_id"])
    op.create_index("ix_semantic_memory_indices_user_id", "semantic_memory_indices", ["user_id"])
    op.create_index("ix_semantic_memory_indices_embedding_id", "semantic_memory_indices", ["embedding_id"])
    op.create_index("ix_semantic_memory_indices_content_hash", "semantic_memory_indices", ["content_hash"])


def downgrade() -> None:
    op.drop_table("semantic_memory_indices")
    op.drop_table("project_memories")
    op.drop_table("paper_memories")
    op.drop_table("long_term_memories")
    op.drop_table("session_memories")
    op.drop_table("research_user_profiles")

    op.execute("DROP TYPE IF EXISTS project_memory_category")
    op.execute("DROP TYPE IF EXISTS project_memory_importance")
    op.execute("DROP TYPE IF EXISTS paper_memory_type")
    op.execute("DROP TYPE IF EXISTS long_term_memory_category")
    op.execute("DROP TYPE IF EXISTS long_term_memory_importance")
    op.execute("DROP TYPE IF EXISTS session_memory_type")
    op.execute("DROP TYPE IF EXISTS memory_source")
    op.execute("DROP TYPE IF EXISTS memory_importance")
