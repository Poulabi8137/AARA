'use client'

import { motion } from 'framer-motion'
import { EvidencePanel } from '@/components/evidence-panel'
import { mockEvidenceData } from '@/lib/mock-data'
import { GlassCard } from '@/components/ui/glass-card'
import { PageTransition, childVariants } from '@/components/page-transition'

const stats = [
  { label: 'Papers Analyzed', value: '147', gradient: 'from-blue-400 to-cyan-400' },
  { label: 'Key Themes', value: '12', gradient: 'from-purple-400 to-pink-400' },
  { label: 'Key Findings', value: '34', gradient: 'from-green-400 to-emerald-400' },
]

const themes = [
  { theme: 'Deep Learning Applications', papers: 45, keyPoints: ['Convolutional Neural Networks for image processing', 'Transformer models for NLP tasks', 'Attention mechanisms improve model performance'] },
  { theme: 'Federated Learning', papers: 28, keyPoints: ['Privacy-preserving distributed training', 'Challenges in communication efficiency', 'Real-world deployment considerations'] },
  { theme: 'Transfer Learning', papers: 34, keyPoints: ['Domain adaptation strategies', 'Pre-training and fine-tuning approaches', 'Effectiveness across different domains'] },
]

export default function LiteratureReviewPage() {
  return (
    <PageTransition className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">Literature Review</h1>
        <p className="text-sm text-foreground/50">Comprehensive synthesis of research themes and key findings</p>
      </div>

      <motion.div className="grid md:grid-cols-3 gap-4" variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.06 } } }} initial="hidden" animate="visible">
        {stats.map((stat, i) => (
          <motion.div key={i} variants={childVariants}>
            <GlassCard depth="flat" className="p-5">
              <p className="text-xs font-medium text-foreground/50">{stat.label}</p>
              <p className={`text-2xl font-bold mt-1 bg-gradient-to-r ${stat.gradient} bg-clip-text text-transparent`}>{stat.value}</p>
            </GlassCard>
          </motion.div>
        ))}
      </motion.div>

      <div className="space-y-3">
        <h2 className="text-sm font-semibold">Research Themes</h2>
        <motion.div className="space-y-3" variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.06 } } }} initial="hidden" animate="visible">
          {themes.map((item, i) => (
            <motion.div key={i} variants={childVariants}>
              <GlassCard depth="flat" className="p-5">
                <div className="space-y-3">
                  <div>
                    <h3 className="text-sm font-semibold">{item.theme}</h3>
                    <p className="text-xs text-foreground/50 mt-0.5">Based on {item.papers} papers</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-foreground/60">Key Points:</p>
                    <ul className="space-y-0.5">
                      {item.keyPoints.map((point, idx) => (
                        <li key={idx} className="text-xs text-foreground/60 flex gap-1.5">
                          <span className="text-primary">•</span> {point}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </motion.div>
      </div>

      <div className="space-y-3">
        <h2 className="text-sm font-semibold">Evidence-Backed Findings</h2>
        <div className="space-y-3">
          <EvidencePanel evidence={mockEvidenceData.literatureReviewEvidence} title="Deep Learning Dominates NLP" compact={false} />
          <EvidencePanel evidence={mockEvidenceData.federatedLearningEvidence} title="Privacy-Preserving Training Gains Traction" compact={false} />
        </div>
      </div>

      <div className="space-y-3">
        <h2 className="text-sm font-semibold">Key Findings</h2>
        <div className="grid md:grid-cols-2 gap-3">
          {[
            'Transformer architectures have become the standard in NLP with 89% of recent papers utilizing them',
            'Federated learning adoption is increasing but communication efficiency remains a critical bottleneck',
            'Transfer learning effectiveness is domain-dependent with variable performance across different fields',
            'Privacy-preserving techniques add 15-30% computational overhead on average',
          ].map((finding, i) => (
            <motion.div key={i} variants={childVariants} className="p-4 rounded-xl bg-primary/5 border border-primary/20">
              <p className="text-xs text-foreground/70 leading-relaxed">{finding}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </PageTransition>
  )
}
