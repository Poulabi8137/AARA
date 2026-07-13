'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { FileEdit, Plus, FileText, Loader2, Eye } from 'lucide-react'
import { GlassCard } from '@/components/ui/glass-card'
import { PageTransition, childVariants } from '@/components/page-transition'
import { apiClient } from '@/lib/api-client'
import { safeGetItem } from '@/lib/utils'

interface Proposal {
  id: string
  project_id: string
  proposed_title: string
  problem_statement: string
  domain: string | null
  created_at: string
}

interface Paper {
  id: string
  project_id: string
  title: string
  status: string
  abstract: string
  created_at: string
  metrics?: { composite_score: number } | null
}

export default function PaperAuthoringPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<'proposals' | 'papers'>('proposals')
  const [proposals, setProposals] = useState<Proposal[]>([])
  const [papers, setPapers] = useState<Paper[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [projectId, setProjectId] = useState<string>('')
  const [showCreateProposal, setShowCreateProposal] = useState(false)
  const [gapId, setGapId] = useState('')
  const [domain, setDomain] = useState('')
  const [objective, setObjective] = useState('')
  const [keywords, setKeywords] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    const project = safeGetItem('currentProjectId')
    if (project) setProjectId(project)
    loadData()
  }, [])

  const loadData = async () => {
    setIsLoading(true)
    try {
      const projId = safeGetItem('currentProjectId')
      if (!projId) { setIsLoading(false); return }
      setProjectId(projId)

      const [proposalsRes, papersRes] = await Promise.all([
        apiClient.get(`/papers/proposals/${projId}`).catch(() => ({ data: [] })),
        apiClient.get(`/papers/project/${projId}`).catch(() => ({ data: { papers: [], total: 0 } })),
      ])
      setProposals(proposalsRes.data || [])
      setPapers(papersRes.data?.papers || [])
    } catch {
    }
    setIsLoading(false)
  }

  const handleCreateProposal = async () => {
    if (!projectId || !objective) return
    setCreating(true)
    try {
      await apiClient.post('/papers/proposal', {
        project_id: projectId,
        gap_id: gapId || undefined,
        domain: domain || 'General',
        objective,
        keywords: keywords || '',
      })
      setShowCreateProposal(false)
      setGapId('')
      setDomain('')
      setObjective('')
      setKeywords('')
      await loadData()
    } catch {
    }
    setCreating(false)
  }

  const handleGeneratePaper = async (proposalId: string) => {
    if (!projectId || !proposalId) return
    try {
      await apiClient.post('/papers/generate', {
        project_id: projectId,
        proposal_id: proposalId,
      })
      await loadData()
    } catch {
    }
  }

  const statusBadge = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'bg-gray-500/20 text-gray-300',
      proposal: 'bg-blue-500/20 text-blue-300',
      generated: 'bg-green-500/20 text-green-300',
      editing: 'bg-yellow-500/20 text-yellow-300',
      complete: 'bg-emerald-500/20 text-emerald-300',
      failed: 'bg-red-500/20 text-red-300',
    }
    return (
      <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${colors[status] || 'bg-gray-500/20 text-gray-300'}`}>
        {status}
      </span>
    )
  }

  return (
    <PageTransition>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Paper Authoring</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Generate IEEE-style research papers from proposals
            </p>
          </div>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setShowCreateProposal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium"
          >
            <Plus className="w-4 h-4" />
            New Proposal
          </motion.button>
        </div>

        <div className="flex gap-1 border-b border-border/40">
          {(['proposals', 'papers'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab === 'proposals' ? 'Proposals' : 'Papers'} ({tab === 'proposals' ? proposals.length : papers.length})
            </button>
          ))}
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : activeTab === 'proposals' ? (
          <div className="space-y-4">
            {proposals.length === 0 ? (
              <GlassCard className="p-12 text-center">
                <FileEdit className="w-12 h-12 mx-auto text-muted-foreground/40 mb-4" />
                <h3 className="text-lg font-medium mb-2">No proposals yet</h3>
                <p className="text-sm text-muted-foreground max-w-md mx-auto mb-4">
                  Create a research proposal from your project&apos;s research gaps to begin paper authoring.
                </p>
              </GlassCard>
            ) : (
              proposals.map((p) => (
                <motion.div key={p.id} variants={childVariants}>
                  <GlassCard className="p-5 hover:border-primary/20 transition-all cursor-pointer"
                    onClick={() => router.push(`/research/papers/author/proposal/${p.id}`)}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold truncate">{p.proposed_title}</h3>
                        <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{p.problem_statement}</p>
                        <div className="flex items-center gap-3 mt-3 text-xs text-muted-foreground">
                          {p.domain && <span>Domain: {p.domain}</span>}
                          <span>{new Date(p.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <motion.button
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          onClick={(e) => { e.stopPropagation(); handleGeneratePaper(p.id) }}
                          className="px-3 py-1.5 bg-primary/10 text-primary rounded-lg text-xs font-medium hover:bg-primary/20"
                        >
                          Generate Paper
                        </motion.button>
                        <Eye className="w-4 h-4 text-muted-foreground" />
                      </div>
                    </div>
                  </GlassCard>
                </motion.div>
              ))
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {papers.length === 0 ? (
              <GlassCard className="p-12 text-center">
                <FileText className="w-12 h-12 mx-auto text-muted-foreground/40 mb-4" />
                <h3 className="text-lg font-medium mb-2">No papers generated yet</h3>
                <p className="text-sm text-muted-foreground max-w-md mx-auto mb-4">
                  Generate a paper from a proposal to see it here.
                </p>
              </GlassCard>
            ) : (
              papers.map((p) => (
                <motion.div key={p.id} variants={childVariants}>
                  <GlassCard className="p-5 hover:border-primary/20 transition-all cursor-pointer"
                    onClick={() => router.push(`/research/papers/author/${p.id}`)}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold truncate">{p.title}</h3>
                          {statusBadge(p.status)}
                        </div>
                        <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{p.abstract}</p>
                        <div className="flex items-center gap-3 mt-3 text-xs text-muted-foreground">
                          <span>{new Date(p.created_at).toLocaleDateString()}</span>
                          {p.metrics && <span>Quality: {p.metrics.composite_score.toFixed(0)}/100</span>}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Eye className="w-4 h-4 text-muted-foreground" />
                      </div>
                    </div>
                  </GlassCard>
                </motion.div>
              ))
            )}
          </div>
        )}

        {showCreateProposal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
               onClick={() => setShowCreateProposal(false)}>
            <GlassCard className="w-full max-w-lg p-6" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
              <h2 className="text-lg font-semibold mb-4">Create Research Proposal</h2>
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-muted-foreground">Research Objective *</label>
                  <textarea
                    value={objective}
                    onChange={(e) => setObjective(e.target.value)}
                    className="w-full mt-1 px-3 py-2 bg-muted/30 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 min-h-[80px]"
                    placeholder="Describe your research objective..."
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Domain</label>
                    <input
                      value={domain}
                      onChange={(e) => setDomain(e.target.value)}
                      className="w-full mt-1 px-3 py-2 bg-muted/30 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                      placeholder="e.g., AI, Healthcare"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Keywords</label>
                    <input
                      value={keywords}
                      onChange={(e) => setKeywords(e.target.value)}
                      className="w-full mt-1 px-3 py-2 bg-muted/30 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                      placeholder="Comma-separated"
                    />
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground">Gap ID (optional)</label>
                  <input
                    value={gapId}
                    onChange={(e) => setGapId(e.target.value)}
                    className="w-full mt-1 px-3 py-2 bg-muted/30 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                    placeholder="Reference to research gap"
                  />
                </div>
              </div>
              <div className="flex gap-3 mt-6 justify-end">
                <button onClick={() => setShowCreateProposal(false)}
                  className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground">
                  Cancel
                </button>
                <button onClick={handleCreateProposal} disabled={creating || !objective}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium disabled:opacity-50">
                  {creating ? 'Creating...' : 'Create Proposal'}
                </button>
              </div>
            </GlassCard>
          </div>
        )}
      </div>
    </PageTransition>
  )
}
