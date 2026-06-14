'use client'

import { motion } from 'framer-motion'
import { EvidencePanel } from '@/components/evidence-panel'
import { mockEvidenceData } from '@/lib/mock-data'
import { TrendingUp, AlertCircle } from 'lucide-react'
import { GlassCard } from '@/components/ui/glass-card'
import { PageTransition, childVariants } from '@/components/page-transition'

const gaps = [
  { id: '1', title: 'Efficient Transformer Fine-tuning for Edge Devices', severity: 'critical' as const, description: 'Current fine-tuning methods require substantial computational resources, limiting deployment on resource-constrained devices.', relatedTopics: ['Model Compression', 'Quantization', 'Knowledge Distillation'], paperCount: 34 },
  { id: '2', title: 'Communication Efficiency in Federated Learning', severity: 'critical' as const, description: 'Communication overhead remains a bottleneck in federated learning systems, causing 15-30% performance degradation.', relatedTopics: ['Compression', 'Gradient Aggregation', 'Quantization'], paperCount: 28 },
  { id: '3', title: 'Interpretability of Transformer Attention Mechanisms', severity: 'high' as const, description: 'While transformers achieve excellent performance, understanding and interpreting their attention patterns remains challenging.', relatedTopics: ['Explainability', 'Attention Analysis', 'Interpretable ML'], paperCount: 19 },
  { id: '4', title: 'Privacy-Utility Tradeoff Quantification', severity: 'high' as const, description: 'Lack of standardized metrics for measuring privacy-utility tradeoffs.', relatedTopics: ['Differential Privacy', 'Evaluation Metrics', 'Privacy Theory'], paperCount: 12 },
  { id: '5', title: 'Cross-Domain Transfer Learning Benchmarks', severity: 'medium' as const, description: 'Limited standardized benchmarks for evaluating transfer learning effectiveness across diverse domains.', relatedTopics: ['Benchmark Design', 'Domain Adaptation', 'Evaluation'], paperCount: 8 },
]

const severityStyles = { critical: 'border-red-500/20 bg-red-500/5', high: 'border-orange-500/20 bg-orange-500/5', medium: 'border-yellow-500/20 bg-yellow-500/5' }
const severityBadges = { critical: 'bg-red-500/10 text-red-400 border-red-500/20', high: 'bg-orange-500/10 text-orange-400 border-orange-500/20', medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' }

export default function GapAnalysisPage() {
  return (
    <PageTransition className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">Research Gap Analysis</h1>
        <p className="text-sm text-foreground/50">Identify unexplored research opportunities and bottlenecks in the field</p>
      </div>

      <motion.div className="grid md:grid-cols-4 gap-4" initial="hidden" animate="visible" variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.06 } } }}>
        {[
          { label: 'Total Gaps', value: '5', gradient: 'from-red-400 to-orange-400' },
          { label: 'Critical', value: '2', gradient: 'from-red-400 to-red-500' },
          { label: 'High Priority', value: '2', gradient: 'from-orange-400 to-yellow-400' },
          { label: 'Avg Coverage', value: '34%', gradient: 'from-yellow-400 to-green-400' },
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
        <h2 className="text-sm font-semibold">Identified Research Gaps</h2>
        <motion.div className="space-y-3" initial="hidden" animate="visible" variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.06 } } }}>
          {gaps.map((gap) => (
            <motion.div key={gap.id} variants={childVariants}>
              <div className={`p-5 rounded-xl border ${severityStyles[gap.severity] || 'border-border/40 bg-background/40 backdrop-blur-xl'} transition-all hover:shadow-lg`}>
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-sm font-semibold">{gap.title}</h3>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${severityBadges[gap.severity]}`}>
                          {gap.severity.charAt(0).toUpperCase() + gap.severity.slice(1)}
                        </span>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-xs text-foreground/50">{gap.paperCount} papers</p>
                    </div>
                  </div>
                  <p className="text-xs text-foreground/60 leading-relaxed">{gap.description}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {gap.relatedTopics.map((topic) => (
                      <span key={topic} className="px-2 py-0.5 rounded-full text-[10px] bg-primary/10 text-primary border border-primary/20">{topic}</span>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>

      <div className="space-y-3">
        <h2 className="text-sm font-semibold">Evidence-Backed Gap Analysis</h2>
        <EvidencePanel evidence={mockEvidenceData.gapAnalysisEvidence} title="Key Research Gaps with Evidence" />
      </div>

      <div className="space-y-3">
        <h2 className="text-sm font-semibold">Research Recommendations</h2>
        <div className="grid md:grid-cols-2 gap-4">
          {[
            { title: 'High Impact Opportunities', items: ['Develop efficient fine-tuning methods for transformers', 'Reduce communication overhead in federated learning', 'Create standardized privacy-utility metrics'], icon: TrendingUp },
            { title: 'Emerging Areas', items: ['Hybrid sparse transformer architectures', 'Cross-domain federated learning', 'Neural architecture search for efficiency'], icon: AlertCircle },
          ].map((rec, i) => {
            const Icon = rec.icon
            return (
              <GlassCard key={i} depth="flat" className="p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Icon className="w-4 h-4 text-primary" />
                  <h3 className="text-sm font-semibold">{rec.title}</h3>
                </div>
                <ul className="space-y-1">
                  {rec.items.map((item, idx) => (
                    <li key={idx} className="text-xs text-foreground/60 flex gap-1.5"><span className="text-primary">•</span> {item}</li>
                  ))}
                </ul>
              </GlassCard>
            )
          })}
        </div>
      </div>
    </PageTransition>
  )
}
