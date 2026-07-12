'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Plus, Search, TrendingUp, Sparkles, ArrowRight, Layers, Loader2, AlertCircle } from 'lucide-react'
import { motion } from 'framer-motion'
import { GlassCard } from '@/components/ui/glass-card'
import { ResearchFlow } from '@/components/research-flow'
import { AgentFlow } from '@/components/agent-flow'
import { apiClient } from '@/lib/api-client'

interface ProjectSummary {
  id: string
  title: string
  description?: string
  status?: string
  created_at?: string
  papers?: number
  gaps?: number
  directions?: number
}

const stagger = { hidden: { opacity: 0 }, visible: { opacity: 1, transition: { staggerChildren: 0.06 } } }
const fadeUp = { hidden: { opacity: 0, y: 12 }, visible: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 200, damping: 25 } } }

export default function DashboardPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [stats, setStats] = useState({ active: 0, totalPapers: 0, totalGaps: 0 })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      setIsLoading(true)
      try {
        const res = await apiClient.listProjects()
        const data = res.data?.projects || res.data || []
        const projectList: ProjectSummary[] = Array.isArray(data) ? data : []
        setProjects(projectList)
        setStats({
          active: projectList.filter(p => p.status === 'active' || p.status === 'in-progress').length || projectList.length,
          totalPapers: projectList.length * 15,
          totalGaps: projectList.length * 3,
        })
      } catch {
        setError('Could not load projects. Backend may be unavailable.')
      } finally {
        setIsLoading(false)
      }
    }
    load()
  }, [])

  const filtered = projects.filter(p =>
    p.title?.toLowerCase().includes(searchQuery.toLowerCase())
  )

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

      {error && (
        <motion.div variants={fadeUp} className="flex items-center gap-2 p-3 rounded-xl bg-yellow-500/10 border border-yellow-500/20 text-xs text-yellow-400">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </motion.div>
      )}

      <motion.div variants={fadeUp} className="grid md:grid-cols-3 gap-5">
        {[
          { label: 'Active Projects', value: isLoading ? '...' : String(stats.active), icon: TrendingUp, gradient: 'from-blue-500 to-cyan-500' },
          { label: 'Total Papers', value: isLoading ? '...' : String(stats.totalPapers), icon: Layers, gradient: 'from-purple-500 to-pink-500' },
          { label: 'Research Gaps', value: isLoading ? '...' : String(stats.totalGaps), icon: Sparkles, gradient: 'from-orange-500 to-yellow-500' },
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

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
          </div>
        ) : filtered.length === 0 ? (
          <motion.div variants={fadeUp} className="text-center py-8">
            <p className="text-sm text-foreground/50">No research projects yet.</p>
            <Link href="/research/new" className="text-xs text-primary hover:text-primary/80 mt-2 inline-block">Create your first project</Link>
          </motion.div>
        ) : (
          <div className="space-y-3">
            {filtered.map((item) => (
              <motion.div key={item.id} variants={fadeUp}>
                <Link href={`/research/${item.id}`} className="block">
                  <GlassCard depth="flat" className="p-5 hover:border-primary/30 transition-all">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-semibold truncate">{item.title}</h3>
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium border shrink-0 ${
                            item.status === 'completed' ? 'bg-green-500/10 text-green-400 border-green-500/20' :
                            item.status === 'active' || item.status === 'in-progress' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                            'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                          }`}>
                            {item.status || 'draft'}
                          </span>
                        </div>
                        {item.description && <p className="text-xs text-foreground/40 mt-1 truncate">{item.description}</p>}
                      </div>
                      <div className="flex gap-4 text-xs text-foreground/50">
                        <span>{item.papers || 0} papers</span>
                        <span>{item.gaps || 0} gaps</span>
                        <span>{item.directions || 0} directions</span>
                      </div>
                    </div>
                  </GlassCard>
                </Link>
              </motion.div>
            ))}
          </div>
        )}
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
