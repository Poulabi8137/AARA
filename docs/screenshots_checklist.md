# Screenshots Checklist

**Generated**: June 2026
**Purpose**: Screenshots for README, portfolio, and demo assets

---

## Required Screenshots

### 1. Landing Page
- **Route**: `/`
- **What to capture**: Hero section with "AARA — AI Research Operating System" tagline, feature grid, and agent flow visualization
- **Resolution**: 1920x1080
- **File**: `screenshots/landing.png`

### 2. Dashboard
- **Route**: `/dashboard`
- **What to capture**: Stats cards (Active Projects, Total Papers, Research Gaps), search bar, research pipeline visualization, recent research list with status badges
- **Key elements**: Gradient stat cards, project list with status badges, AgentFlow component
- **File**: `screenshots/dashboard.png`

### 3. Research Creation
- **Route**: `/research/new`
- **What to capture**: Preset topic cards (AI/ML, Healthcare, Climate, CS), custom query input, objective textarea
- **File**: `screenshots/create-research.png`

### 4. Research Project Detail
- **Route**: `/research/[id]`
- **What to capture**: Project title, status badge, stats grid (Papers, Gaps, Directions, Status), Agent Pipeline visualization, navigation tabs, action cards
- **Key elements**: Tab bar, "Run Agents" button, GlassCard design
- **File**: `screenshots/project-detail.png`

### 5. Agent Pipeline
- **Route**: `/research/monitoring`
- **What to capture**: Stats cards (Completed/Running/Pending/Failed), AgentFlow pipeline, execution details with progress bars, timeline chart
- **Key elements**: Color-coded status badges, progress bars, Recharts bar chart
- **File**: `screenshots/agent-monitoring.png`

### 6. Papers Repository
- **Route**: `/research/papers`
- **What to capture**: Search bar, sort dropdown, paper list with relevance scores, source badges, star favorites
- **Key elements**: Relevance bars, citation counts, year display
- **File**: `screenshots/papers.png`

### 7. Literature Review
- **Route**: `/research/literature`
- **What to capture**: Stats cards (Papers Analyzed, Key Themes, Key Findings), research themes with key points, evidence panels, key findings grid
- **File**: `screenshots/literature-review.png`

### 8. Gap Analysis
- **Route**: `/research/gaps`
- **What to capture**: Stats cards, severity-coded gap cards (critical/high/medium), related topic tags, recommendations
- **Key elements**: Red/orange/yellow severity gradients, topic chips
- **File**: `screenshots/gap-analysis.png`

### 9. Novel Directions
- **Route**: `/research/directions`
- **What to capture**: Stats cards, direction cards with impact badges, research approach, potential impact callout, research timeline
- **Key elements**: Lightbulb icons, green/blue/purple impact badges
- **File**: `screenshots/novel-directions.png`

### 10. Report Generation
- **Route**: `/research/report`
- **What to capture**: Template selection cards (Academic, Executive, Custom), customization panel with section checkboxes, export format buttons
- **Key elements**: Selected template highlighting, section checkboxes
- **File**: `screenshots/report-generation.png`

### 11. Citation Manager
- **Route**: `/research/citations`
- **What to capture**: Format cards (APA/MLA/Chicago/BibTeX), generated citations list with copy/export buttons, citation actions
- **Key elements**: Monospace citation text, Copy button feedback
- **File**: `screenshots/citations.png`

### 12. Auth — Login
- **Route**: `/auth/login`
- **What to capture**: Branded two-column layout with AARA OS branding, login form
- **File**: `screenshots/login.png`

### 13. Architecture Diagram
- **Source**: `docs/architecture.md`
- **What to capture**: System architecture showing frontend → backend → agents → vector store → database flow
- **File**: `screenshots/architecture.png`

---

## Optional Screenshots

| Screenshot | Route | When |
|-----------|-------|------|
| Settings | `/settings` | Portfolio — shows API configuration UI |
| Agent execution with running state | `/research/monitoring` | Live demo — shows animated pipeline |
| Error state | Any route | Portfolio — shows error boundaries |
| Empty state | `/dashboard` (no projects) | Portfolio — shows empty states |
| Mobile responsive | Any route | README — shows responsive design |

---

## Screenshot Tooling

- **Browser**: Chrome DevTools — 1920x1080 viewport
- **Tool**: Full Page Screen Capture extension for full-page shots
- **Format**: PNG
- **Naming**: `screenshots/<name>.png`

## Automation

```bash
# Requires puppeteer or playwright
npx playwright install chromium
node scripts/capture-screenshots.mjs
```

## Portfolio Usage

| Screenshot | Best For |
|-----------|----------|
| Dashboard + Pipeline | README hero image |
| Agent Monitoring | Technical interview — shows agent orchestration |
| Gap Analysis + Directions | Product interview — shows AI-generated insights |
| Report Generation | Portfolio — shows end-to-end workflow |
| Architecture | System design interview |
