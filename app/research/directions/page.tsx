'use client'

import { motion } from 'framer-motion'
import { EvidencePanel } from '@/components/evidence-panel'
import { mockEvidenceData } from '@/lib/mock-data'
import { Lightbulb, BookOpen, ChevronRight } from 'lucide-react'
import { GlassCard } from '@/components/ui/glass-card'
import { PageTransition, childVariants } from '@/components/page-transition'

const directions = [
  { id: '1', title: 'Hybrid Sparse-Dense Transformer Architectures', description: 'Combining sparse and dense attention mechanisms to reduce computational overhead.', researchApproach: 'Develop adaptive routing mechanisms that select between sparse and dense attention based on input characteristics.', potentialImpact: 'Could reduce transformer inference time by 40-60% while maintaining 98%+ accuracy.', relatedGaps: ['Efficient Transformer Fine-tuning', 'Cross-Domain Transfer Learning'], estimatedImpact: 'High' },
  { id: '2', title: 'Privacy-Preserving Transfer Learning', description: 'Combining differential privacy with transfer learning for strict privacy guarantees.', researchApproach: 'Develop techniques for privatizing model parameters during transfer.', potentialImpact: 'Enable privacy-compliant knowledge transfer in healthcare, finance, and other sensitive domains.', relatedGaps: ['Privacy-Utility Tradeoff Quantification', 'Communication Efficiency'], estimatedImpact: 'High' },
  { id: '3', title: 'Cross-Domain Federated Ensemble Learning', description: 'Develop ensemble methods leveraging heterogeneous models across domains in federated settings.', researchApproach: 'Design domain-specific experts within a federated framework with mixture-of-experts routing.', potentialImpact: 'Could improve model generalization by 20-35% and reduce communication by 50%.', relatedGaps: ['Cross-Domain Transfer Learning Benchmarks', 'Communication Efficiency'], estimatedImpact: 'Medium-High' },
  { id: '4', title: 'Interpretable Attention-based Decision Making', description: 'Extract human-interpretable decision rules from transformer attention patterns.', researchApproach: 'Create attention factorization techniques and visualization tools.', potentialImpact: 'Enable safe deployment of transformers in high-stakes domains like healthcare, law, and finance.', relatedGaps: ['Interpretability of Transformer Attention', 'Privacy-Utility Tradeoff'], estimatedImpact: 'Medium' },
]

const impactColors: Record<string, string> = { High: 'bg-green-500/10 text-green-400 border-green-500/20', 'Medium-High': 'bg-blue-500/10 text-blue-400 border-blue-500/20', Medium: 'bg-purple-500/10 text-purple-400 border-purple-500/20' }

export default function NovelDirectionsPage() {
  return (
    <PageTransition className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">Novel Research Directions</h1>
        <p className="text-sm text-foreground/50">Innovative research opportunities grounded in literature analysis</p>
      </div>

      <motion.div className="grid md:grid-cols-3 gap-4" initial="hidden" animate="visible" variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.06 } } }}>
        {[
          { label: 'Novel Directions', value: '4', gradient: 'from-blue-400 to-cyan-400' },
          { label: 'High Impact', value: '2', gradient: 'from-purple-400 to-pink-400' },
          { label: 'Avg Confidence', value: '76%', gradient: 'from-green-400 to-emerald-400' },
        ].map((stat, i) => (
          <motion.div key={i} variants={childVariants}>
            <GlassCard depth="flat" className="p-5">
              <p className="text-xs font-medium text-foreground/50">{stat.label}</p>
              <p className={`text-2xl font-bold mt-1 bg-gradient-to-r ${stat.gradient} bg-clip-text text-transparent`}>{stat.value}</p>
            </GlassCard>
          </motion.div>
        ))}
      </motion.div>

      <div className="space-y-3">
        <h2 className="text-sm font-semibold">Recommended Research Directions</h2>
        <motion.div className="space-y-4" initial="hidden" animate="visible" variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.06 } } }}>
          {directions.map((direction) => (
            <motion.div key={direction.id} variants={childVariants}>
              <GlassCard depth="flat" className="overflow-hidden">
                <div className="p-5 space-y-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1.5">
                        <Lightbulb className="w-4 h-4 text-yellow-400 shrink-0" />
                        <h3 className="text-sm font-semibold">{direction.title}</h3>
                      </div>
                      <p className="text-xs text-foreground/60">{direction.description}</p>
                    </div>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium border shrink-0 ${impactColors[direction.estimatedImpact] || ''}`}>
                      {direction.estimatedImpact} Impact
                    </span>
                  </div>

                  <div className="space-y-1.5">
                    <h4 className="text-xs font-semibold text-foreground/60 flex items-center gap-1.5">
                      <BookOpen className="w-3.5 h-3.5" /> Research Approach
                    </h4>
                    <p className="text-xs text-foreground/60 pl-5">{direction.researchApproach}</p>
                  </div>

                  <div className="p-3 rounded-lg bg-primary/5 border border-primary/20">
                    <p className="text-xs font-semibold text-foreground/70 mb-1">Potential Impact</p>
                    <p className="text-xs text-foreground/60">{direction.potentialImpact}</p>
                  </div>

                  {direction.relatedGaps.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      <span className="text-[10px] text-foreground/40">Addresses:</span>
                      {direction.relatedGaps.map((gap) => (
                        <span key={gap} className="px-2 py-0.5 rounded-full text-[10px] bg-accent/10 text-accent border border-accent/20">{gap}</span>
                      ))}
                    </div>
                  )}

                  <button className="w-full py-2 rounded-lg border border-primary/30 text-primary text-xs font-medium hover:bg-primary/5 transition-colors flex items-center justify-center gap-1.5">
                    View Details & Evidence <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </motion.div>
      </div>

      <div className="space-y-3">
        <h2 className="text-sm font-semibold">Evidence-Backed Directions</h2>
        <EvidencePanel evidence={mockEvidenceData.novelDirectionsEvidence} title="Supporting Evidence for Novel Directions" />
      </div>

      <div className="space-y-3">
        <h2 className="text-sm font-semibold">Suggested Research Timeline</h2>
        <div className="space-y-2">
          {[
            { phase: 'Phase 1: Literature', duration: '2-3 months', tasks: 'Deep dive into related works and identify key papers' },
            { phase: 'Phase 2: Feasibility', duration: '1-2 months', tasks: 'Conduct proof-of-concept experiments' },
            { phase: 'Phase 3: Development', duration: '4-6 months', tasks: 'Develop core methodology and algorithms' },
            { phase: 'Phase 4: Evaluation', duration: '2-3 months', tasks: 'Comprehensive benchmarking and validation' },
            { phase: 'Phase 5: Publication', duration: '1-2 months', tasks: 'Write papers and submit to conferences' },
          ].map((item, i) => (
            <motion.div key={i} variants={childVariants} className="flex gap-4 p-4 rounded-xl bg-background/40 backdrop-blur-xl border border-border/40">
              <div className="w-28 shrink-0">
                <p className="text-xs font-semibold">{item.phase}</p>
                <p className="text-[10px] text-foreground/50 mt-0.5">{item.duration}</p>
              </div>
              <p className="text-xs text-foreground/60">{item.tasks}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </PageTransition>
  )
}
