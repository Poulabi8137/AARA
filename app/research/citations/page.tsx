'use client'

import { motion } from 'framer-motion'
import { Copy, Download, BookOpen } from 'lucide-react'
import { GlassCard } from '@/components/ui/glass-card'
import { PageTransition, childVariants } from '@/components/page-transition'

const formats = [
  { format: 'APA', shortcode: 'apa', example: 'Author, A. (2024). Title.' },
  { format: 'MLA', shortcode: 'mla', example: 'Author. "Title." Journal, 2024.' },
  { format: 'Chicago', shortcode: 'chicago', example: 'Author, A. Title. Journal, 2024.' },
  { format: 'BibTeX', shortcode: 'bibtex', example: '@article{key, author={...}}' },
]

export default function CitationManagerPage() {
  return (
    <PageTransition className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">Citation Manager</h1>
        <p className="text-sm text-foreground/50">Generate and manage citations in multiple formats</p>
      </div>

      <motion.div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4" initial="hidden" animate="visible" variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.06 } } }}>
        {formats.map((fmt, i) => (
          <motion.div key={i} variants={childVariants}>
            <GlassCard depth="flat" className="p-5 group cursor-pointer">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold">{fmt.format}</h3>
                  <Copy className="w-3.5 h-3.5 text-foreground/30 group-hover:text-foreground/60 transition-colors" />
                </div>
                <p className="text-[10px] text-foreground/50 font-mono">{fmt.example}</p>
                <button className="w-full py-1.5 rounded-lg bg-primary/10 text-primary text-[10px] font-medium hover:bg-primary/20 transition-colors">
                  Generate
                </button>
              </div>
            </GlassCard>
          </motion.div>
        ))}
      </motion.div>

      <div className="space-y-3">
        <h2 className="text-sm font-semibold">Generated Citations</h2>
        <motion.div className="space-y-2" initial="hidden" animate="visible" variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.04 } } }}>
          {Array.from({ length: 5 }).map((_, i) => (
            <motion.div key={i} variants={childVariants}>
              <GlassCard depth="flat" className="p-4">
                <div className="space-y-2">
                  <p className="text-xs font-mono text-foreground/60 leading-relaxed">
                    Smith, J., Johnson, A. (2024). Deep Learning in Healthcare. Nature Medicine, 30(4), 1-15.
                  </p>
                  <div className="flex gap-2">
                    <button className="text-[10px] px-2 py-1 rounded-lg bg-primary/10 text-primary hover:bg-primary/20 transition-colors flex items-center gap-1">
                      <Copy className="w-3 h-3" /> Copy
                    </button>
                    <button className="text-[10px] px-2 py-1 rounded-lg bg-primary/10 text-primary hover:bg-primary/20 transition-colors flex items-center gap-1">
                      <Download className="w-3 h-3" /> Export
                    </button>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </motion.div>
      </div>

      <GlassCard depth="flat" className="p-5 space-y-4">
        <h3 className="text-sm font-semibold flex items-center gap-2">
          <BookOpen className="w-4 h-4" />
          Citation Actions
        </h3>
        <div className="grid md:grid-cols-2 gap-3">
          <button className="px-4 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors shadow-lg shadow-primary/20">
            Generate All Citations
          </button>
          <button className="px-4 py-2 rounded-xl border border-border/50 text-foreground/70 text-xs font-medium hover:bg-muted/30 transition-colors">
            Export Bibliography
          </button>
        </div>
      </GlassCard>
    </PageTransition>
  )
}
