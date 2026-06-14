"""create evaluation tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evaluation_benchmarks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("expected_findings", JSON, nullable=False),
        sa.Column("expected_subtopics", JSON, nullable=False),
        sa.Column("expected_references", JSON, nullable=False),
        sa.Column("expected_quality_score", sa.Float, nullable=True),
        sa.Column("tags", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "evaluation_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("research_projects.id"), nullable=True),
        sa.Column("execution_id", UUID(as_uuid=True), sa.ForeignKey("agent_executions.id"), nullable=True),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("overall_quality_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("coverage_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("citation_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("hallucination_risk_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("gap_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("evidence_strength_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("source_diversity_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("summary_quality_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("run_metadata", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "evaluation_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("evaluation_runs.id"), nullable=False),
        sa.Column("metric_name", sa.String(128), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("weight", sa.Float, nullable=False, server_default="1"),
        sa.Column("details", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("evaluation_metrics")
    op.drop_table("evaluation_runs")
    op.drop_table("evaluation_benchmarks")
