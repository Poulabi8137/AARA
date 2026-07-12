"""Add paper authoring models (Proposal, Paper, PaperSection, etc.)

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-16
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_projects.id"), nullable=False),
        sa.Column("gap_id", sa.String(256), nullable=True),
        sa.Column("proposed_title", sa.String(512), nullable=False),
        sa.Column("problem_statement", sa.Text, nullable=False),
        sa.Column("motivation", sa.Text, nullable=False),
        sa.Column("research_questions", postgresql.JSON, nullable=False),
        sa.Column("hypothesis", sa.Text, nullable=False),
        sa.Column("objectives", postgresql.JSON, nullable=False),
        sa.Column("expected_contributions", postgresql.JSON, nullable=False),
        sa.Column("proposed_methodology", sa.Text, nullable=False),
        sa.Column("evaluation_strategy", sa.Text, nullable=False),
        sa.Column("future_scope", sa.Text, nullable=False),
        sa.Column("keywords", postgresql.JSON, nullable=False),
        sa.Column("domain", sa.String(256), nullable=True),
        sa.Column("base_paper_analysis", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "base_paper_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_projects.id"), nullable=False),
        sa.Column("source_doi", sa.String(1024), nullable=True),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("source_filename", sa.String(512), nullable=True),
        sa.Column("abstract", sa.Text, nullable=True),
        sa.Column("keywords", postgresql.JSON, nullable=True),
        sa.Column("methodology", sa.Text, nullable=True),
        sa.Column("dataset_description", sa.Text, nullable=True),
        sa.Column("experiments", sa.Text, nullable=True),
        sa.Column("limitations", sa.Text, nullable=True),
        sa.Column("future_work", sa.Text, nullable=True),
        sa.Column("references", postgresql.JSON, nullable=True),
        sa.Column("originality_metadata", postgresql.JSON, nullable=True),
        sa.Column("extracted_text", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "papers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_projects.id"), nullable=False),
        sa.Column("proposal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("proposals.id"), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("abstract", sa.Text, nullable=False),
        sa.Column("keywords", postgresql.JSON, nullable=False),
        sa.Column("authors", sa.String(1024), nullable=False),
        sa.Column("status", sa.Enum("draft", "proposal", "proposal_complete", "generating", "generated", "editing", "reviewing", "complete", "failed", name="paper_status", create_constraint=True), nullable=False),
        sa.Column("ieee_content", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "paper_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id"), nullable=False),
        sa.Column("section_number", sa.Integer, nullable=False),
        sa.Column("section_title", sa.String(256), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("word_count", sa.Integer, nullable=False),
        sa.Column("status", sa.Enum("draft", "reviewed", "approved", "needs_revision", name="section_status", create_constraint=True), nullable=False),
        sa.Column("evidence_classifications", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "paper_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id"), nullable=False),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("paper_sections.id"), nullable=True),
        sa.Column("section_title", sa.String(256), nullable=True),
        sa.Column("operation", sa.Enum("rewrite", "expand", "condense", "improve_tone", "regenerate", "add_citations", "improve_depth", name="paper_operation", create_constraint=True), nullable=False),
        sa.Column("old_content", sa.Text, nullable=True),
        sa.Column("new_content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "paper_citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id"), nullable=False),
        sa.Column("citation_key", sa.String(128), nullable=False),
        sa.Column("authors", sa.String(1024), nullable=True),
        sa.Column("title", sa.String(1024), nullable=True),
        sa.Column("year", sa.Integer, nullable=True),
        sa.Column("journal", sa.String(512), nullable=True),
        sa.Column("volume", sa.String(64), nullable=True),
        sa.Column("pages", sa.String(64), nullable=True),
        sa.Column("doi", sa.String(256), nullable=True),
        sa.Column("url", sa.String(1024), nullable=True),
        sa.Column("ieee_format", sa.Text, nullable=True),
        sa.Column("verified", sa.Boolean, nullable=False),
        sa.Column("verification_errors", postgresql.JSON, nullable=True),
    )
    op.create_table(
        "paper_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id"), nullable=False),
        sa.Column("format", sa.String(16), nullable=False),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("file_path", sa.String(1024), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "paper_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id"), nullable=False, unique=True),
        sa.Column("novelty_score", sa.Float, nullable=False),
        sa.Column("citation_coverage", sa.Float, nullable=False),
        sa.Column("evidence_strength", sa.Float, nullable=False),
        sa.Column("methodology_quality", sa.Float, nullable=False),
        sa.Column("writing_quality", sa.Float, nullable=False),
        sa.Column("logical_consistency", sa.Float, nullable=False),
        sa.Column("academic_tone", sa.Float, nullable=False),
        sa.Column("section_completeness", sa.Float, nullable=False),
        sa.Column("composite_score", sa.Float, nullable=False),
        sa.Column("details", postgresql.JSON, nullable=True),
        sa.Column("suggestions", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "evidence_statements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id"), nullable=False),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("paper_sections.id"), nullable=True),
        sa.Column("statement", sa.Text, nullable=False),
        sa.Column("classification", sa.Enum("supported", "weakly_supported", "needs_citation", "speculative", name="evidence_class", create_constraint=True), nullable=False),
        sa.Column("citation_key", sa.String(128), nullable=True),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("evidence_statements")
    op.drop_table("paper_metrics")
    op.drop_table("paper_exports")
    op.drop_table("paper_citations")
    op.drop_table("paper_revisions")
    op.drop_table("paper_sections")
    op.drop_table("papers")
    op.drop_table("base_paper_analyses")
    op.drop_table("proposals")
    op.execute("DROP TYPE IF EXISTS paper_status")
    op.execute("DROP TYPE IF EXISTS section_status")
    op.execute("DROP TYPE IF EXISTS paper_operation")
    op.execute("DROP TYPE IF EXISTS evidence_class")
