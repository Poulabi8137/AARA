'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import {
  ArrowLeft, Loader2, Save, RefreshCw,
  Edit3, Expand, Shrink, PenTool, Quote, BarChart3, Download, CheckCircle,
  Scissors
} from 'lucide-react'
import { GlassCard } from '@/components/ui/glass-card'
import { PageTransition } from '@/components/page-transition'
import { apiClient } from '@/lib/api-client'

interface PaperSection {
  id: string
  paper_id: string
  section_number: number
  section_title: string
  content: string
  word_count: number
  status: string
}

interface PaperData {
  id: string
  title: string
  abstract: string
  keywords: string[]
  status: string
  sections: PaperSection[]
  citations: unknown[]
  metrics: { composite_score?: number } | null
}

interface ReviewData {
  novelty_score: number
  citation_coverage: number
  evidence_strength: number
  methodology_quality: number
  writing_quality: number
  logical_consistency: number
  academic_tone: number
  section_completeness: number
  composite_score: number
  suggestions: string[]
}

export default function PaperEditorPage() {
  const params = useParams()
  const router = useRouter()
  const paperId = params.paperId as string
  const [paper, setPaper] = useState<PaperData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [activeSection, setActiveSection] = useState<number>(0)
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [activeOp, setActiveOp] = useState('')
  const [showReview, setShowReview] = useState(false)
  const [review, setReview] = useState<ReviewData | null>(null)
  const [showCitations, setShowCitations] = useState(false)
  const [citationResult, setCitationResult] = useState<Record<string, unknown> | null>(null)
  const [showEvidence, setShowEvidence] = useState(false)
  const [evidenceResult, setEvidenceResult] = useState<Record<string, unknown> | null>(null)
  const [loadingAction, setLoadingAction] = useState('')

  useEffect(() => {
    if (paperId) loadPaper()
  }, [paperId])

  const loadPaper = async () => {
    setIsLoading(true)
    try {
      const res = await apiClient.get(`/papers/${paperId}`)
      setPaper(res.data)
      if (res.data.sections?.length > 0) {
        setEditContent(res.data.sections[0].content)
      }
    } catch {
    }
    setIsLoading(false)
  }

  const currentSection = paper?.sections?.[activeSection]

  const handleSectionSelect = (idx: number) => {
    setActiveSection(idx)
    setEditing(false)
    if (paper?.sections[idx]) {
      setEditContent(paper.sections[idx].content)
    }
  }

  const handleEditToggle = () => {
    if (!editing && currentSection) {
      setEditContent(currentSection.content)
    }
    setEditing(!editing)
  }

  const handleSaveEdit = async () => {
    if (!currentSection || !editContent) return
    setSaving(true)
    try {
      const res = await apiClient.put(`/papers/${paperId}/section/${currentSection.id}?content=${encodeURIComponent(editContent)}`)
      const updated = res.data
      setPaper(prev => prev ? {
        ...prev,
        sections: prev.sections.map(s => s.id === updated.id ? updated : s)
      } : prev)
      setEditing(false)
    } catch {
    }
    setSaving(false)
  }

  const handleSectionOp = async (op: string) => {
    if (!currentSection) return
    setActiveOp(op)
    setLoadingAction(op)
    try {
      const res = await apiClient.post(`/papers/${paperId}/sections/${currentSection.id}/rewrite`, { operation: op })
      const { new_content } = res.data
      setEditContent(new_content)
      setPaper(prev => prev ? {
        ...prev,
        sections: prev.sections.map(s =>
          s.id === currentSection.id ? { ...s, content: new_content, word_count: new_content.split(' ').length } : s
        )
      } : prev)
    } catch {
    }
    setActiveOp('')
    setLoadingAction('')
  }

  const handleQualityReview = async () => {
    setShowReview(true)
    setLoadingAction('review')
    try {
      const res = await apiClient.post(`/papers/${paperId}/quality-review`)
      setReview(res.data)
      setPaper(prev => prev ? { ...prev, metrics: res.data } : prev)
    } catch {
    }
    setLoadingAction('')
  }

  const handleCitationValidation = async () => {
    setShowCitations(true)
    setLoadingAction('citations')
    try {
      const res = await apiClient.post(`/papers/${paperId}/validate-citations`)
      setCitationResult(res.data)
    } catch {
    }
    setLoadingAction('')
  }

  const handleEvidenceValidation = async () => {
    setShowEvidence(true)
    setLoadingAction('evidence')
    try {
      const res = await apiClient.post(`/papers/${paperId}/validate-evidence`)
      setEvidenceResult(res.data)
    } catch {}
    setLoadingAction('')
  }

  const handleExport = async (fmt: string) => {
    try {
      const res = await apiClient.get(`/papers/${paperId}/download/${fmt}`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `${paper?.title?.slice(0, 50) || 'paper'}.${fmt}`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch {
    }
  }

  const operations = [
    { key: 'rewrite', icon: RefreshCw, label: 'Rewrite', color: 'bg-blue-500/10 text-blue-400' },
    { key: 'expand', icon: Expand, label: 'Expand', color: 'bg-green-500/10 text-green-400' },
    { key: 'condense', icon: Shrink, label: 'Condense', color: 'bg-orange-500/10 text-orange-400' },
    { key: 'improve_tone', icon: PenTool, label: 'Improve Tone', color: 'bg-purple-500/10 text-purple-400' },
    { key: 'add_citations', icon: Quote, label: 'Add Citations', color: 'bg-cyan-500/10 text-cyan-400' },
    { key: 'improve_depth', icon: Scissors, label: 'Improve Depth', color: 'bg-pink-500/10 text-pink-400' },
  ]

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!paper) {
    return (
      <div className="text-center py-12 text-muted-foreground">Paper not found</div>
    )
  }

  return (
    <PageTransition>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => router.push('/research/papers/author')} className="p-2 hover:bg-muted/30 rounded-lg">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl font-bold tracking-tight">{paper.title}</h1>
              <p className="text-xs text-muted-foreground">
                {paper.sections.length} sections | {paper.citations.length} citations
                {paper.metrics && ` | Quality: ${paper.metrics.composite_score?.toFixed(0) || 'N/A'}/100`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => handleExport('pdf')} className="flex items-center gap-1.5 px-3 py-1.5 bg-muted/30 rounded-lg text-xs font-medium hover:bg-muted/50">
              <Download className="w-3.5 h-3.5" /> PDF
            </button>
            <button onClick={() => handleExport('docx')} className="flex items-center gap-1.5 px-3 py-1.5 bg-muted/30 rounded-lg text-xs font-medium hover:bg-muted/50">
              <Download className="w-3.5 h-3.5" /> DOCX
            </button>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-2">
          {(['review', 'citations', 'evidence'] as const).map((action) => {
            const icons = { review: BarChart3, citations: Quote, evidence: CheckCircle }
            const labels = { review: 'Quality Review', citations: 'Validate Citations', evidence: 'Validate Evidence' }
            const Icon = icons[action]
            const loading = loadingAction === action
            const handlers = { review: handleQualityReview, citations: handleCitationValidation, evidence: handleEvidenceValidation }
            return (
              <button key={action} onClick={handlers[action]} disabled={loading}
                className="flex items-center justify-center gap-2 px-3 py-2 bg-primary/10 hover:bg-primary/20 rounded-lg text-xs font-medium transition-colors disabled:opacity-50">
                {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Icon className="w-3.5 h-3.5" />}
                {labels[action]}
              </button>
            )
          })}
        </div>

        <div className="grid grid-cols-4 gap-6">
          <div className="col-span-1 space-y-1">
            <h3 className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wider">Sections</h3>
            {paper.sections.map((s, i) => (
              <button key={s.id} onClick={() => handleSectionSelect(i)}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors ${
                  i === activeSection
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-muted-foreground hover:bg-muted/30'
                }`}>
                <span className="text-[10px] opacity-60 mr-1">{s.section_number}.</span>
                {s.section_title}
                <span className="block text-[10px] opacity-40 mt-0.5">{s.word_count} words</span>
              </button>
            ))}
          </div>

          <div className="col-span-3 space-y-4">
            {currentSection && (
              <>
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">
                    {currentSection.section_number}. {currentSection.section_title}
                  </h2>
                  <div className="flex items-center gap-2">
                    {editing ? (
                      <>
                        <button onClick={handleSaveEdit} disabled={saving}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-green-500/20 text-green-400 rounded-lg text-xs font-medium">
                          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                          Save
                        </button>
                        <button onClick={() => setEditing(false)}
                          className="px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground">
                          Cancel
                        </button>
                      </>
                    ) : (
                      <button onClick={handleEditToggle}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-muted/30 rounded-lg text-xs font-medium hover:bg-muted/50">
                        <Edit3 className="w-3.5 h-3.5" /> Edit
                      </button>
                    )}
                  </div>
                </div>

                {editing ? (
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="w-full min-h-[400px] p-4 bg-muted/10 border border-border rounded-lg text-sm font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-primary/30 resize-y"
                  />
                ) : (
                  <GlassCard className="p-5">
                    <div className="prose prose-invert prose-sm max-w-none">
                      {currentSection.content.split('\n\n').map((para, i) => (
                        <p key={i} className="mb-3 text-sm leading-relaxed text-foreground/80">{para}</p>
                      ))}
                    </div>
                  </GlassCard>
                )}

                <div className="flex flex-wrap gap-2">
                  {operations.map(op => (
                    <motion.button key={op.key}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => handleSectionOp(op.key)}
                      disabled={activeOp === op.key}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${op.color} disabled:opacity-50`}>
                      {activeOp === op.key ? <Loader2 className="w-3 h-3 animate-spin" /> : <op.icon className="w-3 h-3" />}
                      {op.label}
                    </motion.button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {showReview && review && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowReview(false)}>
            <GlassCard className="w-full max-w-2xl max-h-[80vh] overflow-y-auto p-6" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
              <h2 className="text-lg font-semibold mb-4">Quality Review</h2>
              <div className="grid grid-cols-2 gap-3 mb-4">
                {[
                  { label: 'Novelty', value: review.novelty_score },
                  { label: 'Citation Coverage', value: review.citation_coverage },
                  { label: 'Evidence Strength', value: review.evidence_strength },
                  { label: 'Methodology', value: review.methodology_quality },
                  { label: 'Writing Quality', value: review.writing_quality },
                  { label: 'Logical Consistency', value: review.logical_consistency },
                  { label: 'Academic Tone', value: review.academic_tone },
                  { label: 'Completeness', value: review.section_completeness },
                ].map(m => (
                  <div key={m.label} className="p-3 bg-muted/20 rounded-lg">
                    <div className="text-xs text-muted-foreground mb-1">{m.label}</div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-muted/30 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${m.value >= 70 ? 'bg-green-500' : m.value >= 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                          style={{ width: `${m.value}%` }} />
                      </div>
                      <span className="text-xs font-medium">{m.value.toFixed(0)}</span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="text-center mb-4">
                <span className="text-2xl font-bold">{review.composite_score?.toFixed(1)}</span>
                <span className="text-sm text-muted-foreground ml-1">/100</span>
              </div>
              {review.suggestions?.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium mb-2">Suggestions</h3>
                  <ul className="space-y-1">
                    {review.suggestions.map((s: string, i: number) => (
                      <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                        <span className="text-primary mt-0.5">•</span> {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <button onClick={() => setShowReview(false)}
                className="w-full mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium">
                Close
              </button>
            </GlassCard>
          </div>
        )}

        {showCitations && citationResult && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowCitations(false)}>
            <GlassCard className="w-full max-w-xl max-h-[80vh] overflow-y-auto p-6" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
              <h2 className="text-lg font-semibold mb-4">Citation Validation</h2>
              <div className="flex items-center gap-3 mb-4">
                <div className={`px-3 py-1.5 rounded-lg text-sm font-medium ${(citationResult as Record<string, unknown>).has_issues ? 'bg-yellow-500/20 text-yellow-300' : 'bg-green-500/20 text-green-300'}`}>
                  {(citationResult as Record<string, unknown>).has_issues ? 'Has Issues' : 'All Clear'}
                </div>
                <span className="text-xs text-muted-foreground">{String((citationResult as Record<string, unknown>).verified_count ?? 0)}/{String((citationResult as Record<string, unknown>).total ?? 0)} verified</span>
              </div>
              {((citationResult as Record<string, unknown>).citations as Record<string, unknown>[] | undefined)?.map((entry, i) => {
                const c = entry as Record<string, unknown>
                return (
                <div key={i} className="p-3 bg-muted/20 rounded-lg mb-2 text-xs">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium">{String(c.citation_key ?? '')}</span>
                    {!!c.is_fabricated && <span className="px-1.5 py-0.5 bg-red-500/20 text-red-300 rounded text-[10px]">Fabricated?</span>}
                    {!!c.is_duplicate && <span className="px-1.5 py-0.5 bg-yellow-500/20 text-yellow-300 rounded text-[10px]">Duplicate</span>}
                    {!!c.has_doi && <span className="px-1.5 py-0.5 bg-green-500/20 text-green-300 rounded text-[10px]">Has DOI</span>}
                  </div>
                  {(c.verification_notes as unknown[])?.length > 0 && (
                    <ul className="text-[10px] text-muted-foreground mt-1 space-y-0.5">
                      {(c.verification_notes as string[]).map((n, j) => <li key={j}>• {n}</li>)}
                    </ul>
                  )}
                </div>
                )
              })}
              <button onClick={() => setShowCitations(false)}
                className="w-full mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium">
                Close
              </button>
            </GlassCard>
          </div>
        )}

        {showEvidence && evidenceResult && (() => {
          const er = evidenceResult as Record<string, unknown>
          const erCoverage = (er.coverage || {}) as Record<string, number>
          const erSections = (er.sections || []) as Record<string, unknown>[]
          return (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowEvidence(false)}>
            <GlassCard className="w-full max-w-xl max-h-[80vh] overflow-y-auto p-6" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
              <h2 className="text-lg font-semibold mb-4">Evidence Validation</h2>
              <div className="grid grid-cols-4 gap-2 mb-4">
                {Object.entries(erCoverage).filter(([k]) => k !== 'total').map(([k, v]) => (
                  <div key={k} className="text-center p-2 bg-muted/20 rounded-lg">
                    <div className="text-lg font-bold">{v}</div>
                    <div className="text-[10px] text-muted-foreground capitalize">{k.replace('_', ' ')}</div>
                  </div>
                ))}
              </div>
              <div className="mb-4">
                <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                  <span>Supported Ratio</span>
                  <span>{((er.overall_supported_ratio as number) * 100).toFixed(0)}%</span>
                </div>
                <div className="h-2 bg-muted/30 rounded-full overflow-hidden">
                  <div className="h-full bg-green-500 rounded-full"
                    style={{ width: `${(er.overall_supported_ratio as number) * 100}%` }} />
                </div>
              </div>
              {erSections.slice(0, 3).map((sec, i) => (
                <div key={i} className="mb-3">
                  <h3 className="text-xs font-medium mb-1">{String(sec.section_title ?? '')}</h3>
                  <div className="flex gap-1">
                    {Object.entries((sec.coverage || {}) as Record<string, number>).filter(([k]) => k !== 'total').map(([k, v]) => (
                      <span key={k} className={`px-1.5 py-0.5 rounded text-[10px] ${
                        k === 'supported' ? 'bg-green-500/20 text-green-300' :
                        k === 'needs_citation' ? 'bg-yellow-500/20 text-yellow-300' :
                        k === 'speculative' ? 'bg-purple-500/20 text-purple-300' :
                        'bg-orange-500/20 text-orange-300'
                      }`}>
                        {k.replace('_', ' ')}: {v}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
              <button onClick={() => setShowEvidence(false)}
                className="w-full mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium">
                Close
              </button>
            </GlassCard>
          </div>
          )
        })()}
      </div>
    </PageTransition>
  )
}
