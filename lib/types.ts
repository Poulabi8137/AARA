/**
 * Core types for AARA platform
 * Defines the data structures for research workflow
 */

export interface User {
  id: string;
  email: string;
  name: string;
  role?: string;
  avatar?: string;
  createdAt: string;
}

export interface Paper {
  id: string;
  title: string;
  authors: string[];
  abstract: string;
  year: number;
  doi?: string;
  url?: string;
  citations: number;
  source: 'arxiv' | 'pubmed' | 'scholar' | 'other';
  relevanceScore?: number;
  summary?: string;
}

export interface EvidencePanel {
  sourcePapers: Paper[];
  supportingEvidence: string[];
  confidenceScore: number; // 0-100
  agentReasoningSummary: string;
  relatedCitations: Citation[];
}

export interface ResearchGap {
  id: string;
  title: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  relatedTopics: string[];
  evidence: EvidencePanel;
}

export interface NovelDirection {
  id: string;
  title: string;
  description: string;
  researchApproach: string;
  potentialImpact: string;
  relatedGaps: string[];
  evidence: EvidencePanel;
}

export interface LiteratureReview {
  id: string;
  researchId: string;
  themes: ReviewTheme[];
  keyFindings: string[];
  gaps: ResearchGap[];
  generatedAt: string;
}

export interface ReviewTheme {
  name: string;
  papers: Paper[];
  summary: string;
  keyPoints: string[];
}

export interface Citation {
  id: string;
  paperId: string;
  format: 'apa' | 'mla' | 'chicago' | 'bibtex';
  text: string;
}

export interface Report {
  id: string;
  researchId: string;
  title: string;
  template: 'academic' | 'executive' | 'comprehensive';
  sections: ReportSection[];
  generatedAt: string;
  lastModified: string;
}

export interface ReportSection {
  id: string;
  title: string;
  content: string;
  type: 'summary' | 'literature' | 'gaps' | 'directions' | 'citations';
  order: number;
}

export interface AgentExecution {
  id: string;
  researchId: string;
  type: 'planner' | 'retriever' | 'summarizer' | 'analyzer' | 'generator';
  status: 'pending' | 'running' | 'completed' | 'failed';
  startedAt: string;
  completedAt?: string;
  progress: number; // 0-100
  logs: AgentLog[];
  result?: any;
  error?: string;
}

export interface AgentLog {
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'debug';
  message: string;
  data?: any;
}

export interface AgentGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'agent' | 'data' | 'process';
  status: 'pending' | 'running' | 'completed' | 'failed';
  x: number;
  y: number;
}

export interface GraphEdge {
  from: string;
  to: string;
  label?: string;
}

export interface Research {
  id: string;
  userId: string;
  topic: string;
  description?: string;
  status: 'draft' | 'in-progress' | 'completed' | 'archived';
  createdAt: string;
  updatedAt: string;
  papers: Paper[];
  literatureReview?: LiteratureReview;
  gapAnalysis: ResearchGap[];
  novelDirections: NovelDirection[];
  citations: Citation[];
  report?: Report;
  agents: AgentExecution[];
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface ResearchState {
  research: Research | null;
  isLoading: boolean;
  error: string | null;
}

// ── Paper Authoring Types ──────────────────────────────────────────────

export interface Proposal {
  id: string;
  project_id: string;
  gap_id?: string;
  proposed_title: string;
  problem_statement: string;
  motivation: string;
  research_questions: string[];
  hypothesis: string;
  objectives: string[];
  expected_contributions: string[];
  proposed_methodology: string;
  evaluation_strategy: string;
  future_scope: string;
  keywords: string[];
  domain?: string;
  base_paper_analysis?: any;
  created_at: string;
  updated_at: string;
}

export interface PaperSection {
  id: string;
  paper_id: string;
  section_number: number;
  section_title: string;
  content: string;
  word_count: number;
  status: 'draft' | 'reviewed' | 'approved' | 'needs_revision';
  evidence_classifications?: any;
}

export interface PaperCitation {
  id: string;
  paper_id: string;
  citation_key: string;
  authors?: string;
  title?: string;
  year?: number;
  journal?: string;
  doi?: string;
  url?: string;
  ieee_format?: string;
  verified: boolean;
  verification_errors?: string[];
}

export interface PaperMetrics {
  id: string;
  paper_id: string;
  novelty_score: number;
  citation_coverage: number;
  evidence_strength: number;
  methodology_quality: number;
  writing_quality: number;
  logical_consistency: number;
  academic_tone: number;
  section_completeness: number;
  composite_score: number;
  suggestions?: string[];
}

export interface AcademicPaper {
  id: string;
  project_id: string;
  proposal_id?: string;
  title: string;
  abstract: string;
  keywords: string[];
  authors: string;
  status: 'draft' | 'proposal' | 'generated' | 'editing' | 'reviewing' | 'complete';
  sections: PaperSection[];
  citations: PaperCitation[];
  metrics?: PaperMetrics;
  created_at: string;
  updated_at: string;
}
