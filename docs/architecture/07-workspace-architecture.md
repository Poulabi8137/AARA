# Document 07 — Workspace Architecture

## Workspace Data Model

A workspace is the primary organizational unit. It owns all research artifacts for a single research topic.

```
Workspace
  ├── Metadata (name, description, research_topic, status)
  ├── Members (user_id → role mapping)
  ├── Settings (LLM provider, embedding model, search sources, auto-approval)
  ├── Papers (library of imported/uploaded papers)
  │   ├── Authors (linked through paper_authors)
  │   ├── Chunks (text segments for embedding)
  │   ├── Embeddings (per model)
  │   ├── Citations (papers cited by this paper)
  │   └── References (papers this paper cites)
  ├── Workflows (research process executions)
  │   ├── Steps (individual agent executions)
  │   ├── Execution Logs (per-agent telemetry)
  │   └── Approval Checkpoints (human-in-the-loop)
  ├── Analyses (literature reviews, gap analyses, comparisons)
  ├── Ideas (generated research ideas)
  ├── Drafts (paper drafts + citations)
  └── Evaluation Reports (quality metrics)
```

## Workspace CRUD API Design

```python
# Pydantic schemas

class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    research_topic: str | None = None

class WorkspaceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    research_topic: str | None = None
    status: Literal["active", "archived"] | None = None

class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    research_topic: str | None
    status: str
    member_count: int
    paper_count: int
    workflow_count: int
    created_at: datetime
    updated_at: datetime
```

## Workspace Isolation via RLS

```sql
-- Users can only see workspaces they own or are members of
CREATE POLICY workspace_select ON workspaces FOR SELECT
    USING (
        owner_id = auth.uid() OR
        id IN (SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid())
    );

-- Only workspace owner or admin can update
CREATE POLICY workspace_update ON workspaces FOR UPDATE
    USING (
        owner_id = auth.uid() OR
        id IN (SELECT workspace_id FROM workspace_members
               WHERE user_id = auth.uid() AND role = 'admin')
    );

-- Cascade to papers
CREATE POLICY paper_select ON papers FOR SELECT
    USING (workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid())
        OR workspace_id IN (SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid()));

CREATE POLICY paper_insert ON papers FOR INSERT
    WITH CHECK (
        workspace_id IN (SELECT workspace_id FROM workspace_members
                         WHERE user_id = auth.uid() AND role IN ('editor', 'admin'))
        OR workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid())
    );
```

## Workspace Settings (Defaults)

| Setting | Default | Rationale |
|---|---|---|
| `preferred_llm_provider` | `openai` | Best quality for research writing |
| `preferred_llm_model` | `gpt-4o-mini` | Cost-effective, 128K context |
| `embedding_model` | `sentence-transformers/all-MiniLM-L6-v2` | Free, 384-dim, fast |
| `search_sources` | `["semantic_scholar", "arxiv", "crossref"]` | Broadest coverage for free |
| `max_papers_per_search` | 50 | Balances depth vs. API cost |
| `auto_approve_threshold` | `none` | All checkpoints require manual approval |

## Trade-offs

| Decision | Alternative | Why Chosen |
|---|---|---|
| One workspace per topic | Multiple topics per workspace | Simpler data isolation; clearer user mental model |
| Member roles at workspace level | Global roles | Finer-grained collaboration control |
| Workspace settings override user defaults | Only global settings | Per-topic flexibility (CS lit review uses different model than Bio) |
