'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Plus, Search, Clock, TrendingUp, Sparkles, ArrowRight, Layers } from 'lucide-react'
import { motion } from 'framer-motion'
import { GlassCard } from '@/components/ui/glass-card'
import { ResearchFlow } from '@/components/research-flow'
import { AgentFlow } from '@/components/agent-flow'

const recentResearch = [
  { id: '1', topic: 'Machine Learning in Healthcare', status: 'in-progress', papers: 45, gaps: 8, directions: 3, lastModified: '2 hours ago' },
  { id: '2', topic: 'Quantum Computing Applications', status: 'completed', papers: 72, gaps: 12, directions: 7, lastModified: '1 day ago' },
  { id: '3', topic: 'Climate Change Modeling', status: 'draft', papers: 28, gaps: 5, directions: 2, lastModified: '3 days ago' },
]

const stagger = { hidden: { opacity: 0 }, visible: { opacity: 1, transition: { staggerChildren: 0.06 } } }
const fadeUp = { hidden: { opacity: 0, y: 12 }, visible: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 200, damping: 25 } } }

export default function DashboardPage() {
  const [searchQuery, setSearchQuery] = useState('')

  return (
    <motion.div className="space-y-8" variants={stagger} initial="hidden" animate="visible">
      <motion.div variants={fadeUp} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold tracking-tight">Research OS</h1>
            <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-[10px] font-medium border border-primary/20">v2.0</span>
          </div>
          <p className="text-sm text-foreground/50">Your AI-powered research command center</p>
        </div>
        <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
          <Link
            href="/research/new"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium text-sm shadow-lg shadow-primary/20 hover:shadow-xl hover:shadow-primary/30 transition-all"
          >
            <Plus className="w-4 h-4" />
            New Research
          </Link>
        </motion.div>
      </motion.div>

      <motion.div variants={fadeUp} className="grid md:grid-cols-3 gap-5">
        {[
          { label: 'Active Projects', value: '3', icon: TrendingUp, gradient: 'from-blue-500 to-cyan-500' },
          { label: 'Total Papers', value: '145', icon: Layers, gradient: 'from-purple-500 to-pink-500' },
          { label: 'Research Gaps', value: '25', icon: Sparkles, gradient: 'from-orange-500 to-yellow-500' },
        ].map((stat, i) => {
          const Icon = stat.icon
          return (
            <GlassCard key={i} depth="flat" className="p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-foreground/50">{stat.label}</p>
                  <p className={`text-2xl font-bold mt-1 bg-gradient-to-r ${stat.gradient} bg-clip-text text-transparent`}>{stat.value}</p>
                </div>
                <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Icon className="w-4 h-4 text-primary" />
                </div>
              </div>
            </GlassCard>
          )
        })}
      </motion.div>

      <motion.div variants={fadeUp} className="relative">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/30" />
        <input
          type="text"
          placeholder="Search research projects..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-background/40 backdrop-blur-xl border border-border/50 text-sm text-foreground placeholder:text-foreground/30 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all"
        />
      </motion.div>

      <motion.div variants={fadeUp} className="p-5 rounded-xl border border-border/40 bg-background/40 backdrop-blur-xl space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Research Pipeline</h2>
          <span className="text-[10px] text-foreground/40 font-mono">active</span>
        </div>
        <ResearchFlow />
      </motion.div>

      <motion.div className="space-y-4" variants={stagger}>
        <motion.div variants={fadeUp} className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Recent Research</h2>
          <Link href="/research/papers" className="text-xs text-primary hover:text-primary/80 transition-colors flex items-center gap-1">
            View all <ArrowRight className="w-3 h-3" />
          </Link>
        </motion.div>

        <div className="space-y-3">
          {recentResearch.map((item) => (
            <motion.div key={item.id} variants={fadeUp}>
              <Link href={`/research/${item.id}`} className="block">
                <GlassCard depth="flat" className="p-5 hover:border-primary/30 transition-all">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold truncate">{item.topic}</h3>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium border shrink-0 ${
                          item.status === 'completed' ? 'bg-green-500/10 text-green-400 border-green-500/20' :
                          item.status === 'in-progress' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                          'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                        }`}>
                          {item.status.replace('-', ' ')}
                        </span>
                      </div>
                      <p className="text-xs text-foreground/40 mt-1">Modified {item.lastModified}</p>
                    </div>
                    <div className="flex gap-4 text-xs text-foreground/50">
                      <span>{item.papers} papers</span>
                      <span>{item.gaps} gaps</span>
                      <span>{item.directions} directions</span>
                    </div>
                  </div>
                </GlassCard>
              </Link>
            </motion.div>
          ))}
        </div>
      </motion.div>

      <motion.div variants={fadeUp}>
        <GlassCard depth="flat" className="p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Active Agent Pipeline</h2>
            <span className="text-[10px] text-foreground/40 font-mono">live</span>
          </div>
          <AgentFlow />
        </GlassCard>
      </motion.div>
    </motion.div>
  )
}
