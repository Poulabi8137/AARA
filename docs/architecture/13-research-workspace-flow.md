# Document 13 — Research Workspace Flow

## User Journey

```mermaid
sequenceDiagram
    participant User
    participant FE as Frontend
    participant BE as Backend
    participant DB as PostgreSQL
    participant QD as Qdrant
    participant RS as Research APIs
    participant PDF as PDF Pipeline

    Note over User,PDF: PHASE 1: SETUP
    User->>FE: Create workspace "Attention Mechanisms in ViT"
    FE->>BE: POST /api/v1/workspaces
    BE->>DB: INSERT workspace
    BE-->>FE: WorkspaceResponse
    FE->>FE: Navigate to workspace detail

    Note over User,PDF: PHASE 2: DISCOVERY
    User->>FE: Search "vision transformer attention survey"
    FE->>BE: GET /api/v1/workspaces/{id}/search?q=&sources=ss,arxiv
    BE->>RS: Parallel search + dedup
    RS-->>BE: 50 results
    BE-->>FE: PaperCollection
    FE->>User: Paper list with relevance scores

    User->>FE: Select 10 papers to import
    FE->>BE: POST /api/v1/workspaces/{id}/papers/import {ids: [...]}
    BE->>DB: INSERT papers, authors, paper_authors

    Note over User,PDF: PHASE 3: INGESTION
    User->>FE: Upload PDF
    FE->>BE: POST /api/v1/workspaces/{id}/papers/upload
    BE->>PDF: Start PDF Pipeline
    PDF->>DB: INSERT paper (processing)

    Note over PDF: Pipeline runs in background<br/>(stages 1-12)

    PDF->>DB: UPDATE paper (processing=complete)
    PDF->>QD: Upsert chunk embeddings
    PDF-->>BE: PipelineResult
    BE-->>FE: WebSocket "paper.processed"
    FE->>User: Paper detail with extracted sections

    Note over User,PDF: PHASE 4: ANALYSIS (Phase 3 Agents)
    User->>FE: Click "Run Literature Review"
    FE->>BE: POST /api/v1/workflows {type: literature_review}
    BE->>BE: Start workflow → agents execute
    BE-->>FE: WebSocket stream agent events
    FE->>User: Live agent view

    Note over BE: Analysis complete
    BE-->>FE: Workflow completed
    FE->>User: Literature review with themes, gaps
```

## API Endpoints in Workspace Flow

| Step | Method | Endpoint | Purpose |
|---|---|---|---|
| Create workspace | POST | `/api/v1/workspaces` | Create research topic container |
| Search | GET | `/api/v1/workspaces/{id}/search` | Multi-source paper search |
| Import papers | POST | `/api/v1/workspaces/{id}/papers/import` | Import selected papers |
| Upload PDF | POST | `/api/v1/workspaces/{id}/papers/upload` | Upload PDF file |
| View papers | GET | `/api/v1/workspaces/{id}/papers` | List papers in workspace |
| View paper | GET | `/api/v1/papers/{paper_id}` | Paper detail + metadata |
| Semantic search | POST | `/api/v1/workspaces/{id}/search/semantic` | Vector search |
| Start workflow | POST | `/api/v1/workspaces/{id}/workflows` | Begin research workflow |
| Stream events | WS | `/api/v1/ws?workflow_id={id}&token={jwt}` | Real-time agent updates |

## State Transitions

```mermaid
stateDiagram-v2
    [*] --> Empty: Create workspace
    Empty --> HasPapers: Import / Upload
    HasPapers --> HasEmbeddings: PDF processed + embedded
    HasEmbeddings --> AnalysisRunning: Start workflow
    AnalysisRunning --> AwaitingApproval: Agent completes step
    AwaitingApproval --> AnalysisRunning: User approves
    AwaitingApproval --> Cancelled: User rejects
    AnalysisRunning --> AnalysisComplete: All agents done
    AnalysisComplete --> DraftStarted: Start drafting
    DraftStarted --> DraftComplete: Writing agent done
    DraftComplete --> ExportStarted: User exports
    ExportStarted --> [*]: Download complete
```
