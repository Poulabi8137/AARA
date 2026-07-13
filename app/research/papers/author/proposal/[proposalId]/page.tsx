'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { ArrowLeft, FileText, Loader2, CheckCircle, ClipboardList, Lightbulb, Target, ListChecks, BookOpen, FlaskConical, Rocket } from 'lucide-react'
import { GlassCard } from '@/components/ui/glass-card'
import { PageTransition } from '@/components/page-transition'
import { apiClient } from '@/lib/api-client'
import { safeGetItem } from '@/lib/utils'

interface ProposalData {
  id: string
  proposed_title: string
  problem_statement: string
  motivation: string
  research_questions: string[]
  hypothesis: string
  objectives: string[]
  expected_contributions: string[]
  proposed_methodology: string
  evaluation_strategy: string
  future_scope: string
  domain: string | null
  created_at: string
}

export default function ProposalDetailPage() {
  const params = useParams()
  const router = useRouter()
  const proposalId = params.proposalId as string
  const [proposal, setProposal] = useState<ProposalData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    if (!proposalId) return
    loadProposal()
  }, [proposalId])

  const loadProposal = async () => {
    setIsLoading(true)
    try {
      const res = await apiClient.get(`/papers/proposal/${proposalId}`)
      setProposal(res.data)
    } catch {
    }
    setIsLoading(false)
  }

  const handleGeneratePaper = async () => {
    if (!proposal) return
    setGenerating(true)
    try {
      const projectId = safeGetItem('currentProjectId')
      await apiClient.post('/papers/generate', {
        project_id: projectId,
        proposal_id: proposal.id,
      })
      alert('Paper generated successfully!')
      router.push(`/research/papers/author/${proposal.id}`)
    } catch {
      alert('Failed to generate paper. Please try again.')
    }
    setGenerating(false)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!proposal) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        Proposal not found
      </div>
    )
  }

  const sections = [
    { icon: Target, label: 'Problem Statement', content: proposal.problem_statement },
    { icon: Lightbulb, label: 'Motivation', content: proposal.motivation },
    { icon: ClipboardList, label: 'Research Questions', items: proposal.research_questions },
    { icon: BookOpen, label: 'Hypothesis', content: proposal.hypothesis },
    { icon: ListChecks, label: 'Objectives', items: proposal.objectives },
    { icon: FlaskConical, label: 'Expected Contributions', items: proposal.expected_contributions },
    { icon: BookOpen, label: 'Proposed Methodology', content: proposal.proposed_methodology },
    { icon: CheckCircle, label: 'Evaluation Strategy', content: proposal.evaluation_strategy },
    { icon: Rocket, label: 'Future Scope', content: proposal.future_scope },
  ]

  return (
    <PageTransition>
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <button onClick={() => router.back()} className="p-2 hover:bg-muted/30 rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{proposal.proposed_title}</h1>
            <p className="text-sm text-muted-foreground mt-1">
              {proposal.domain && `Domain: ${proposal.domain} | `}
              Created: {new Date(proposal.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleGeneratePaper}
          disabled={generating}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary text-primary-foreground rounded-lg text-sm font-medium disabled:opacity-50"
        >
          {generating ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Generating Paper...</>
          ) : (
            <><FileText className="w-4 h-4" /> Generate IEEE Paper from This Proposal</>
          )}
        </motion.button>

        <div className="space-y-4">
          {sections.map((sec, i) => (
            <GlassCard key={i} className="p-5">
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-primary/10 shrink-0">
                  <sec.icon className="w-4 h-4 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-sm text-muted-foreground mb-2">{sec.label}</h3>
                  {'content' in sec && sec.content ? (
                    <p className="text-sm leading-relaxed">{sec.content}</p>
                  ) : null}
                  {'items' in sec && sec.items ? (
                    <ul className="space-y-1.5">
                      {(sec.items as string[]).map((item, j) => (
                        <li key={j} className="flex items-start gap-2 text-sm">
                          <span className="text-primary mt-1.5 w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              </div>
            </GlassCard>
          ))}
        </div>
      </div>
    </PageTransition>
  )
}
