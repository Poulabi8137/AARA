'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp, AlertCircle, CheckCircle } from 'lucide-react'
import { EvidencePanel as EvidencePanelType } from '@/lib/types'
import { motion, AnimatePresence } from 'framer-motion'
import { GlassCard } from '@/components/ui/glass-card'

interface EvidencePanelProps {
  evidence: EvidencePanelType
  title: string
  compact?: boolean
}

function Shield({ className }: { className: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
    </svg>
  )
}

export function EvidencePanel({ evidence, title, compact = false }: EvidencePanelProps) {
  const [isExpanded, setIsExpanded] = useState(!compact)

  const getConfidenceColor = (score: number) => {
    if (score >= 80) return 'bg-green-500/10 text-green-400 border-green-500/20'
    if (score >= 60) return 'bg-blue-500/10 text-blue-400 border-blue-500/20'
    if (score >= 40) return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
    return 'bg-orange-500/10 text-orange-400 border-orange-500/20'
  }

  return (
    <GlassCard depth="flat" className="overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-5 py-3.5 flex items-center justify-between hover:bg-muted/20 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Shield className="w-4 h-4 text-primary" />
          <div className="text-left">
            <h3 className="text-sm font-semibold">{title}</h3>
            <p className="text-[10px] text-foreground/50">Evidence & Reasoning</p>
          </div>
        </div>
        {isExpanded ? <ChevronUp className="w-4 h-4 text-foreground/50" /> : <ChevronDown className="w-4 h-4 text-foreground/50" />}
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t border-border/30"
          >
            <div className="p-5 space-y-5">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-foreground/70">Confidence Score</span>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getConfidenceColor(evidence.confidenceScore)}`}>
                    {evidence.confidenceScore}%
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-primary to-accent rounded-full transition-all duration-700" style={{ width: `${evidence.confidenceScore}%` }} />
                </div>
              </div>

              <div>
                <h4 className="text-xs font-semibold text-foreground/70 mb-2">Source Papers ({evidence.sourcePapers.length})</h4>
                <div className="space-y-1.5 max-h-40 overflow-y-auto scrollbar-thin">
                  {evidence.sourcePapers.map((paper) => (
                    <div key={paper.id} className="p-2.5 rounded-lg bg-muted/30 border border-border/30">
                      <p className="text-xs font-medium truncate">{paper.title}</p>
                      <p className="text-[10px] text-foreground/50 mt-0.5">
                        {paper.authors.slice(0, 2).join(', ')}{paper.authors.length > 2 && ` +${paper.authors.length - 2}`}
                      </p>
                      {paper.relevanceScore && (
                        <div className="flex items-center gap-2 mt-1.5">
                          <div className="flex-1 h-1 rounded-full bg-muted overflow-hidden">
                            <div className="h-full bg-primary/60 rounded-full" style={{ width: `${paper.relevanceScore}%` }} />
                          </div>
                          <span className="text-[10px] text-foreground/50">{paper.relevanceScore}%</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="text-xs font-semibold text-foreground/70 mb-2">Supporting Evidence</h4>
                <div className="space-y-1.5">
                  {evidence.supportingEvidence.map((item, i) => (
                    <div key={i} className="flex gap-2">
                      <CheckCircle className="w-3.5 h-3.5 text-green-400 flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-foreground/70">{item}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="p-3 rounded-lg bg-primary/5 border border-primary/20">
                <h4 className="text-xs font-semibold mb-1.5 flex items-center gap-1.5">
                  <AlertCircle className="w-3.5 h-3.5" />
                  Agent Reasoning
                </h4>
                <p className="text-xs text-foreground/70 leading-relaxed">{evidence.agentReasoningSummary}</p>
              </div>

              {evidence.relatedCitations.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-foreground/70 mb-2">Related Citations</h4>
                  <div className="space-y-1.5 max-h-28 overflow-y-auto scrollbar-thin">
                    {evidence.relatedCitations.map((citation) => (
                      <div key={citation.id} className="p-2 rounded-lg bg-muted/30 border border-border/30">
                        <p className="text-[10px] text-foreground/60 font-mono">{citation.text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <button className="w-full py-2 rounded-lg border border-primary/30 text-primary text-xs font-medium hover:bg-primary/5 transition-colors">
                Export as Citation
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </GlassCard>
  )
}
