"""research_application_layer

Revision ID: 840fc5d9d682
Revises: 840fc5d9d681
Create Date: 2026-06-22 14:45:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '840fc5d9d682'
down_revision: str | None = '840fc5d9d681'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('research_projects',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('research_goal', sa.Text(), nullable=True),
        sa.Column('key_questions', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], name=op.f('fk_research_projects_workspace_id_workspaces')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_research_projects')),
    )
    op.create_index(op.f('ix_research_projects_workspace_id'), 'research_projects', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_research_projects_status'), 'research_projects', ['status'], unique=False)

    op.create_table('research_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('workflow_id', sa.String(length=255), nullable=True),
        sa.Column('query', sa.Text(), nullable=True),
        sa.Column('agent_phases_completed', sa.JSON(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.Column('total_cost', sa.Float(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['research_projects.id'], name=op.f('fk_research_sessions_project_id_research_projects')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_research_sessions')),
    )
    op.create_index(op.f('ix_research_sessions_project_id'), 'research_sessions', ['project_id'], unique=False)
    op.create_index(op.f('ix_research_sessions_status'), 'research_sessions', ['status'], unique=False)

    op.create_table('research_papers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('authors', sa.JSON(), nullable=True),
        sa.Column('abstract', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('file_type', sa.String(length=10), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('doi', sa.String(length=255), nullable=True),
        sa.Column('arxiv_id', sa.String(length=100), nullable=True),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('publication_year', sa.Integer(), nullable=True),
        sa.Column('venue', sa.String(length=255), nullable=True),
        sa.Column('citation_count', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], name=op.f('fk_research_papers_workspace_id_workspaces')),
        sa.ForeignKeyConstraint(['project_id'], ['research_projects.id'], name=op.f('fk_research_papers_project_id_research_projects')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_research_papers')),
    )
    op.create_index(op.f('ix_research_papers_workspace_id'), 'research_papers', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_research_papers_project_id'), 'research_papers', ['project_id'], unique=False)
    op.create_index(op.f('ix_research_papers_doi'), 'research_papers', ['doi'], unique=False)
    op.create_index(op.f('ix_research_papers_arxiv_id'), 'research_papers', ['arxiv_id'], unique=False)
    op.create_index(op.f('ix_research_papers_source'), 'research_papers', ['source'], unique=False)

    op.create_table('citations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('paper_id', sa.String(length=36), nullable=True),
        sa.Column('raw_citation_text', sa.Text(), nullable=False),
        sa.Column('formatted_citation', sa.Text(), nullable=True),
        sa.Column('style', sa.String(length=20), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('authors', sa.JSON(), nullable=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('journal', sa.String(length=255), nullable=True),
        sa.Column('volume', sa.String(length=50), nullable=True),
        sa.Column('issue', sa.String(length=50), nullable=True),
        sa.Column('pages', sa.String(length=50), nullable=True),
        sa.Column('doi', sa.String(length=255), nullable=True),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('isbn', sa.String(length=20), nullable=True),
        sa.Column('publisher', sa.String(length=255), nullable=True),
        sa.Column('accessed_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], name=op.f('fk_citations_workspace_id_workspaces')),
        sa.ForeignKeyConstraint(['paper_id'], ['research_papers.id'], name=op.f('fk_citations_paper_id_research_papers')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_citations')),
    )
    op.create_index(op.f('ix_citations_workspace_id'), 'citations', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_citations_paper_id'), 'citations', ['paper_id'], unique=False)

    op.create_table('documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=True),
        sa.Column('format', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('citation_count', sa.Integer(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('template_used', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], name=op.f('fk_documents_workspace_id_workspaces')),
        sa.ForeignKeyConstraint(['session_id'], ['research_sessions.id'], name=op.f('fk_documents_session_id_research_sessions')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_documents')),
    )
    op.create_index(op.f('ix_documents_workspace_id'), 'documents', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_documents_session_id'), 'documents', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_table('documents')
    op.drop_table('citations')
    op.drop_table('research_papers')
    op.drop_table('research_sessions')
    op.drop_table('research_projects')
