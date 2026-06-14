# AARA Frontend - API Integration Guide

## Overview

The AARA frontend is a fully type-safe, API-ready research platform built with Next.js 16 and React 19. All backend integration points are pre-configured and ready for connection to your backend API.

## Environment Configuration

Create a `.env.local` file in the project root:

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# Feature Flags
NEXT_PUBLIC_AUTH_ENABLED=true
NEXT_PUBLIC_ENABLE_REAL_TIME_MONITORING=true
NEXT_PUBLIC_ENABLE_WEBSOCKET=true
```

## API Client Setup

The API client is configured in `/lib/api-client.ts` with automatic token management, error handling, and interceptors.

### Example: Making API Calls

```typescript
import { apiClient } from '@/lib/api-client';

// Fetch research papers
const papers = await apiClient.get('/research/papers');

// Create research project
const project = await apiClient.post('/research/projects', {
  title: 'My Research',
  topic: 'AI Safety',
});

// Upload file
const formData = new FormData();
formData.append('file', file);
const response = await apiClient.post('/upload', formData);
```

## Backend API Endpoints Required

### Authentication
- `POST /auth/login` - User login
- `POST /auth/signup` - User registration
- `POST /auth/logout` - User logout
- `GET /auth/me` - Get current user

### Research Projects
- `GET /research/projects` - List user's research projects
- `POST /research/projects` - Create new project
- `GET /research/projects/:id` - Get project details
- `PUT /research/projects/:id` - Update project
- `DELETE /research/projects/:id` - Delete project

### Papers
- `GET /research/papers?query=&skip=&limit=` - Search papers
- `GET /research/papers/:id` - Get paper details
- `POST /research/papers/:id/star` - Star a paper
- `DELETE /research/papers/:id/star` - Unstar a paper

### Literature Review
- `GET /research/:projectId/literature-review` - Get literature review synthesis
- `POST /research/:projectId/literature-review/regenerate` - Regenerate review

### Gap Analysis
- `GET /research/:projectId/gaps` - Get identified research gaps
- `GET /research/:projectId/gaps/:gapId/evidence` - Get gap evidence and citations

### Novel Directions
- `GET /research/:projectId/directions` - Get novel research directions
- `GET /research/:projectId/directions/:directionId/evidence` - Get direction evidence

### Citations
- `GET /research/:projectId/citations?format=apa` - Get citations (supports apa, mla, chicago, bibtex)
- `POST /research/:projectId/citations/export` - Export citations

### Reports
- `POST /research/:projectId/reports/generate` - Generate report with specified sections
- `GET /research/:projectId/reports` - List reports
- `GET /research/:projectId/reports/:reportId` - Get report details
- `POST /research/:projectId/reports/:reportId/export?format=pdf` - Export report

### Agent Monitoring
- `GET /research/:projectId/agents/status` - Get agent execution status
- `GET /research/:projectId/agents/logs` - Get agent execution logs
- `GET /research/:projectId/agents/timeline` - Get execution timeline

## WebSocket Events

Real-time updates via Socket.io at `NEXT_PUBLIC_WS_URL`:

### Client Events (Subscribe)
```typescript
import { subscribeToMonitoringDashboard } from '@/lib/websocket-client';

const unsubscribe = subscribeToMonitoringDashboard(researchId, (data) => {
  console.log('Agent update:', data);
  // { agent, status, progress, timestamp }
});
```

### Server Events to Send
- `agent:update` - Agent execution status changed
- `agent:log` - New log line from agent
- `research:complete` - Research workflow completed
- `evidence:generated` - New evidence panel data available

## Type Definitions

All types are defined in `/lib/types.ts`:

```typescript
interface ResearchProject {
  id: string;
  title: string;
  topic: string;
  status: 'planning' | 'running' | 'completed' | 'error';
  createdAt: Date;
  updatedAt: Date;
}

interface ResearchGap {
  id: string;
  gap: string;
  severity: 'high' | 'medium' | 'low';
  coverage: number; // 0-100
  sourcePapers: Paper[];
  evidence: EvidencePanel;
  confidenceScore: number; // 0-100
}

interface EvidencePanel {
  sourcePapers: { title: string; authors: string[]; year: number }[];
  supportingEvidence: string[];
  confidenceScore: number;
  agentReasoningSummary: string;
  relatedCitations: Citation[];
}
```

## Mock Data

For development without a backend, mock data is available in `/lib/mock-data.ts`. Replace it with actual API calls by updating the components to use the API client instead of mock data.

## State Management

Global state is managed with Zustand in `/lib/store.ts`:

```typescript
import { useResearchStore } from '@/lib/store';

export default function Component() {
  const { researchProject, setResearchProject } = useResearchStore();
  // Use and update state
}
```

## Error Handling

The API client has built-in error handling. Catch errors in your components:

```typescript
try {
  const data = await apiClient.get('/endpoint');
} catch (error) {
  if (error.response?.status === 401) {
    // Handle unauthorized
  } else if (error.response?.status === 404) {
    // Handle not found
  }
}
```

## Authentication Flow

1. User signs up/logs in via `/auth/signup` or `/auth/login`
2. Backend returns JWT token
3. Token is stored in localStorage as `auth_token`
4. API client automatically adds token to all requests via Authorization header
5. On token expiration, user is redirected to login

## Deployment Checklist

- [ ] Set `NEXT_PUBLIC_API_URL` to production API URL
- [ ] Set `NEXT_PUBLIC_WS_URL` to production WebSocket URL
- [ ] Enable CORS on backend for frontend domain
- [ ] Configure authentication strategy (JWT, session cookies, etc.)
- [ ] Set up database for research projects, papers, evidence, etc.
- [ ] Implement agent orchestration system
- [ ] Set up monitoring and logging
- [ ] Configure email notifications (optional)
- [ ] Set up backup and disaster recovery

## Support

For integration support, refer to the component files in `/app/research/` for expected data structures and rendering logic.
