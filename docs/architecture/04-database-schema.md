# Document 04 — Database Schema

## Schema Design Principles

1. **JSONB for flexible metadata** — Paper metadata, analysis content, agent logs all use JSONB to avoid schema migrations per research domain
2. **Composite unique constraints** — Prevent duplicate papers per workspace (DOI + arxiv_id)
3. **Soft deletes** — `status` columns rather than destructive deletes for recoverability
4. **Embedding model versioning** — `model_id` column on `paper_embeddings` enables multiple model versions to coexist
5. **Workflow state persistence** — `current_state` + `recovery_token` on `workflows` enables crash recovery and server restart durability

## All Tables

### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id),  -- Supabase Auth user ID
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    avatar_url TEXT,
    role VARCHAR(20) DEFAULT 'student',  -- student, researcher, admin
    is_active BOOLEAN DEFAULT TRUE,
    monthly_budget_usd DECIMAL(10,2) DEFAULT 5.00,
    embedding_model VARCHAR(200) DEFAULT 'sentence-transformers/all-MiniLM-L6-v2',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### workspaces
```sql
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    research_topic TEXT,
    status VARCHAR(20) DEFAULT 'active',  -- active, archived, deleted
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### workspace_members
```sql
CREATE TABLE workspace_members (
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'editor',  -- viewer, editor, admin
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (workspace_id, user_id)
);
```

### workspace_settings
```sql
CREATE TABLE workspace_settings (
    workspace_id UUID PRIMARY KEY REFERENCES workspaces(id) ON DELETE CASCADE,
    preferred_llm_provider VARCHAR(50) DEFAULT 'openai',
    preferred_llm_model VARCHAR(100) DEFAULT 'gpt-4o-mini',
    embedding_model VARCHAR(200) DEFAULT 'sentence-transformers/all-MiniLM-L6-v2',
    search_sources JSONB DEFAULT '["semantic_scholar", "arxiv", "crossref"]',
    max_papers_per_search INT DEFAULT 50,
    auto_approve_threshold VARCHAR(20) DEFAULT 'none',  -- none, research_only, all
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### papers
```sql
CREATE TABLE papers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    abstract TEXT,
    doi VARCHAR(255),
    arxiv_id VARCHAR(100),
    pmid VARCHAR(100),
    openalex_id VARCHAR(100),
    source VARCHAR(50),  -- semantic_scholar, arxiv, crossref, pubmed, upload
    source_url TEXT,
    pdf_url TEXT,
    pdf_storage_path TEXT,
    publication_date DATE,
    venue VARCHAR(255),
    citation_count INT DEFAULT 0,
    relevance_score DECIMAL(5,4),
    is_imported BOOLEAN DEFAULT FALSE,
    pdf_processing_status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, complete, partial, failed
    pdf_processing_errors JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(workspace_id, doi),
    UNIQUE(workspace_id, arxiv_id)
);
CREATE INDEX idx_papers_workspace ON papers(workspace_id);
CREATE INDEX idx_papers_doi ON papers(doi);
```

### authors
```sql
CREATE TABLE authors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    orcid VARCHAR(50),
    affiliation TEXT,
    external_ids JSONB,  -- {semantic_scholar: "X", openalex: "Y"}
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_authors_name ON authors(name);
```

### paper_authors
```sql
CREATE TABLE paper_authors (
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    author_position INT,
    PRIMARY KEY (paper_id, author_id)
);
CREATE INDEX idx_paper_authors_author ON paper_authors(author_id);
```

### citations
```sql
CREATE TABLE citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    cited_paper_id UUID REFERENCES papers(id) ON DELETE SET NULL,
    cited_doi VARCHAR(255),
    cited_title TEXT,
    citation_context TEXT,
    citation_index INT,
    is_validated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_citations_paper ON citations(paper_id);
```

### paper_references
```sql
CREATE TABLE paper_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    target_paper_id UUID REFERENCES papers(id) ON DELETE SET NULL,
    target_doi VARCHAR(255),
    target_title TEXT,
    raw_reference TEXT,
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### paper_chunks
```sql
CREATE TABLE paper_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    section_name VARCHAR(255),
    token_count INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_chunks_paper ON paper_chunks(paper_id);
```

### paper_embeddings
```sql
CREATE TABLE paper_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    chunk_id UUID REFERENCES paper_chunks(id) ON DELETE SET NULL,
    model_id VARCHAR(200) NOT NULL,
    vector_id VARCHAR(255),  -- Qdrant point ID
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(chunk_id, model_id)
);
CREATE INDEX idx_embeddings_paper ON paper_embeddings(paper_id);
CREATE INDEX idx_embeddings_model ON paper_embeddings(model_id);
```

### workflows
```sql
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    workflow_type VARCHAR(50) NOT NULL,  -- literature_review, gap_analysis, full_research
    status VARCHAR(20) DEFAULT 'pending',  -- pending, planning, running, awaiting_approval, completed, failed, cancelled
    query TEXT NOT NULL,
    idempotency_key VARCHAR(64) UNIQUE,
    current_state JSONB,
    last_agent_id VARCHAR(100),
    last_context_snapshot JSONB,
    recovery_token VARCHAR(100),
    total_cost_usd DECIMAL(10,6),
    total_tokens INT,
    total_duration_ms INT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_workflows_workspace ON workflows(workspace_id);
CREATE INDEX idx_workflows_status ON workflows(status);
```

### workflow_steps
```sql
CREATE TABLE workflow_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    agent_id VARCHAR(100) NOT NULL,
    step_order INT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, running, completed, failed, awaiting_approval
    requires_approval BOOLEAN DEFAULT FALSE,
    input_snapshot JSONB,
    output_snapshot JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);
CREATE INDEX idx_steps_workflow ON workflow_steps(workflow_id);
```

### agent_states
```sql
CREATE TABLE agent_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    agent_id VARCHAR(100) NOT NULL,
    step_id UUID REFERENCES workflow_steps(id),
    status VARCHAR(20) DEFAULT 'initialized',
    current_phase VARCHAR(30) DEFAULT 'idle',
    retry_count INT DEFAULT 0,
    reasoning_history JSONB DEFAULT '[]',
    tool_call_history JSONB DEFAULT '[]',
    observations JSONB DEFAULT '[]',
    reflections JSONB DEFAULT '[]',
    context_token_count INT DEFAULT 0,
    intermediate_outputs JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ,
    duration_ms INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_agent_state_workflow ON agent_states(workflow_id, agent_id);
```

### agent_execution_logs
```sql
CREATE TABLE agent_execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id),
    agent_id VARCHAR(100) NOT NULL,
    execution_number INT NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL,  -- pending, running, success, failed, retrying
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INT,
    cost_usd DECIMAL(10,6),
    token_usage JSONB,
    provider_used VARCHAR(50),
    model_used VARCHAR(100),
    trace_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_logs_workflow ON agent_execution_logs(workflow_id);
CREATE INDEX idx_logs_agent ON agent_execution_logs(agent_id);
```

### approval_checkpoints
```sql
CREATE TABLE approval_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    step_id UUID REFERENCES workflow_steps(id),
    phase VARCHAR(50) NOT NULL,  -- research, idea_gen, draft
    status VARCHAR(20) DEFAULT 'pending',  -- pending, approved, rejected, expired
    input_summary TEXT,
    output_snapshot JSONB,
    user_notes TEXT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    decided_at TIMESTAMPTZ,
    decided_by UUID REFERENCES users(id)
);
CREATE INDEX idx_checkpoints_workflow ON approval_checkpoints(workflow_id);
```

### analyses
```sql
CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    workflow_id UUID REFERENCES workflows(id),
    analysis_type VARCHAR(50) NOT NULL,  -- literature_review, gap_analysis, comparison, timeline
    content JSONB NOT NULL,
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### ideas
```sql
CREATE TABLE ideas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    workflow_id UUID REFERENCES workflows(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    research_gap TEXT,
    methodology_suggestion JSONB,
    overlap_score DECIMAL(5,4),
    overlapping_papers JSONB,
    experiment_plan JSONB,
    status VARCHAR(20) DEFAULT 'generated',  -- generated, approved, rejected, in_progress
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### drafts
```sql
CREATE TABLE drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    workflow_id UUID REFERENCES workflows(id),
    title VARCHAR(500) NOT NULL,
    content JSONB NOT NULL,
    format VARCHAR(20) DEFAULT 'generic',  -- ieee, acm, springer, generic
    status VARCHAR(20) DEFAULT 'draft',  -- draft, review, completed
    word_count INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### draft_citations
```sql
CREATE TABLE draft_citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id UUID NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
    paper_id UUID REFERENCES papers(id),
    citation_key VARCHAR(100),
    doi VARCHAR(255),
    citation_text TEXT,
    section_name VARCHAR(255),
    is_validated BOOLEAN DEFAULT FALSE,
    validation_status VARCHAR(20),  -- valid, invalid, not_found, pending
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### evaluation_reports
```sql
CREATE TABLE evaluation_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    phase VARCHAR(20) DEFAULT 'objective',
    metrics JSONB NOT NULL,
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### audit_logs
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    workspace_id UUID REFERENCES workspaces(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_created ON audit_logs(created_at);
```

### user_preferences
```sql
CREATE TABLE user_preferences (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    theme VARCHAR(10) DEFAULT 'system',
    default_llm_provider VARCHAR(50) DEFAULT 'openai',
    default_embedding_model VARCHAR(200) DEFAULT 'sentence-transformers/all-MiniLM-L6-v2',
    notifications_enabled BOOLEAN DEFAULT TRUE,
    preferences JSONB DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### user_api_keys
```sql
CREATE TABLE user_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,  -- openai, gemini, groq, openrouter
    key_identifier VARCHAR(20) NOT NULL,
    encrypted_key TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### global_memory
```sql
CREATE TABLE global_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    memory_type VARCHAR(50) NOT NULL,  -- prompt_template, execution_pattern, preference
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    tags JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, memory_type, key)
);
```

### cost_metrics
```sql
CREATE TABLE cost_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    workspace_id UUID REFERENCES workspaces(id),
    workflow_id UUID REFERENCES workflows(id),
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    date DATE GENERATED ALWAYS AS (recorded_at::date) STORED,
    llm_prompt_tokens INT DEFAULT 0,
    llm_completion_tokens INT DEFAULT 0,
    llm_total_tokens INT DEFAULT 0,
    llm_cost_usd DECIMAL(10,6) DEFAULT 0,
    embedding_tokens INT DEFAULT 0,
    embedding_cost_usd DECIMAL(10,6) DEFAULT 0,
    api_calls INT DEFAULT 0,
    cache_hits INT DEFAULT 0,
    total_latency_ms INT DEFAULT 0,
    vector_search_latency_ms INT DEFAULT 0,
    provider_breakdown JSONB DEFAULT '{}',
    agent_breakdown JSONB DEFAULT '{}',
    cache_hit_ratio DECIMAL(5,4) DEFAULT 0,
    total_cost_usd DECIMAL(10,6) GENERATED ALWAYS AS (llm_cost_usd + embedding_cost_usd) STORED
);
CREATE INDEX idx_cost_user_date ON cost_metrics(user_id, date);
CREATE INDEX idx_cost_workflow ON cost_metrics(workflow_id);
CREATE INDEX idx_cost_workspace ON cost_metrics(workspace_id);
```

### monthly_cost_summary
```sql
CREATE TABLE monthly_cost_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    year_month VARCHAR(7) NOT NULL,
    total_cost_usd DECIMAL(10,2) DEFAULT 0,
    total_workflows INT DEFAULT 0,
    total_llm_calls INT DEFAULT 0,
    total_embedding_calls INT DEFAULT 0,
    provider_breakdown JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, year_month)
);
```
