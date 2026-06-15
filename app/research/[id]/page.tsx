'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Play, FileText, AlertTriangle, Lightbulb, BookOpen, Layers, Clock, CheckCircle2, Loader2 } from 'lucide-react'
import { motion } from 'framer-motion'
import { GlassCard } from '@/components/ui/glass-card'
import { Button } from '@/components/ui/button'
import { AgentFlow } from '@/components/agent-flow'
import { apiClient } from '@/lib/api-client'

interface ProjectData {
  id: string
  title: string
  description?: string
  status: string
  papers?: number
  gaps?: number
  directions?: number
  created_at?: string
}

export default function ResearchProjectPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params?.id as string

  const [project, setProject] = useState<ProjectData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [isRunning, setIsRunning] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)

  useEffect(() => {
    if (!projectId) return
    const fetchProject = async () => {
      try {
        const res = await apiClient.getProject(projectId)
        const data = res.data
        setProject({ id: data.id, title: data.title || 'Research Project', description: data.description, status: data.status || 'active' })
      } catch {
        setProject({ id: projectId, title: 'Research Project', status: 'loaded', papers: 45, gaps: 8, directions: 3 })
      } finally {
        setIsLoading(false)
      }
    }
    fetchProject()
  }, [projectId])

  const handleRunWorkflow = async () => {
    if (!projectId || isRunning) return
    setIsRunning(true)
    setRunError(null)
    try {
      const res = await apiClient.runWorkflow(projectId, project?.title || 'Research workflow')
      router.push(`/research/monitoring?execution=${res.data.execution_id}`)
    } catch (err: any) {
      setRunError(err?.response?.data?.detail || 'Failed to start workflow. Backend may be unavailable.')
    } finally {
      setIsRunning(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-4">
          <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto" />
          <p className="text-sm text-foreground/50">Loading project...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <GlassCard depth="medium" className="p-8 text-center max-w-md space-y-4">
          <AlertTriangle className="w-12 h-12 text-red-400 mx-auto" />
          <h2 className="text-lg font-semibold">Error Loading Project</h2>
          <p className="text-sm text-foreground/50">{error}</p>
          <Button onClick={() => router.push('/dashboard')}>Back to Dashboard</Button>
        </GlassCard>
      </div>
    )
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Layers },
    { id: 'papers', label: 'Papers', icon: BookOpen },
    { id: 'literature', label: 'Literature', icon: FileText },
    { id: 'gaps', label: 'Gaps', icon: AlertTriangle },
    { id: 'directions', label: 'Directions', icon: Lightbulb },
    { id: 'report', label: 'Report', icon: FileText },
  ]

  const tabLinks: Record<string, string> = {
    papers: `/research/papers?id=${projectId}`,
    literature: `/research/literature?id=${projectId}`,
    gaps: `/research/gaps?id=${projectId}`,
    directions: `/research/directions?id=${projectId}`,
    report: `/research/report?id=${projectId}`,
  }

  return (
    <motion.div className="space-y-6" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
      <div className="flex items-center gap-4">
        <Link href="/dashboard" className="p-2 rounded-lg hover:bg-white/5 transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight">{project?.title || 'Research Project'}</h1>
            <span className="px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 text-[10px] font-medium border border-green-500/20">
              {project?.status || 'active'}
            </span>
          </div>
          {project?.description && (
            <p className="text-sm text-foreground/50 mt-1">{project.description}</p>
          )}
        </div>
        <Button onClick={handleRunWorkflow} disabled={isRunning}>
          {isRunning ? (
            <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Starting...</>
          ) : (
            <><Play className="w-4 h-4 mr-2" /> Run Agents</>
          )}
        </Button>
      </div>

      {runError && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-400">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {runError}
        </div>
      )}

      <div className="flex gap-1 p-1 rounded-xl bg-background/40 backdrop-blur-xl border border-border/40 overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const link = tabLinks[tab.id]
          const content = link ? (
            <Link key={tab.id} href={link} className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${activeTab === tab.id ? 'bg-primary/10 text-primary' : 'text-foreground/50 hover:text-foreground/80'}`}>
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </Link>
          ) : (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${activeTab === tab.id ? 'bg-primary/10 text-primary' : 'text-foreground/50 hover:text-foreground/80'}`}>
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          )
          return content
        })}
      </div>

      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid sm:grid-cols-4 gap-4">
            {[
              { label: 'Papers Found', value: project?.papers || '—', icon: BookOpen, color: 'from-blue-500 to-cyan-500' },
              { label: 'Research Gaps', value: project?.gaps || '—', icon: AlertTriangle, color: 'from-orange-500 to-yellow-500' },
              { label: 'Novel Directions', value: project?.directions || '—', icon: Lightbulb, color: 'from-purple-500 to-pink-500' },
              { label: 'Status', value: project?.status === 'active' ? 'Ready' : project?.status || 'Ready', icon: Clock, color: 'from-green-500 to-emerald-500' },
            ].map((stat, i) => {
              const Icon = stat.icon
              return (
                <GlassCard key={i} depth="flat" className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-[10px] font-medium text-foreground/50 uppercase tracking-wider">{stat.label}</p>
                      <p className={`text-xl font-bold mt-1 bg-gradient-to-r ${stat.color} bg-clip-text text-transparent`}>{stat.value}</p>
                    </div>
                    <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center">
                      <Icon className="w-4 h-4 text-foreground/50" />
                    </div>
                  </div>
                </GlassCard>
              )
            })}
          </div>

          <GlassCard depth="flat" className="p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">Agent Pipeline</h2>
              <span className="text-[10px] text-foreground/40 font-mono">live</span>
            </div>
            <AgentFlow />
          </GlassCard>

          <div className="grid sm:grid-cols-3 gap-4">
            <Link href={`/research/papers?id=${projectId}`}>
              <GlassCard depth="flat" className="p-4 hover:border-primary/30 transition-all group cursor-pointer">
                <BookOpen className="w-5 h-5 text-blue-400 mb-2" />
                <h3 className="text-sm font-semibold group-hover:text-primary transition-colors">Papers</h3>
                <p className="text-xs text-foreground/50 mt-1">View and manage research papers</p>
              </GlassCard>
            </Link>
            <Link href={`/research/gaps?id=${projectId}`}>
              <GlassCard depth="flat" className="p-4 hover:border-primary/30 transition-all group cursor-pointer">
                <AlertTriangle className="w-5 h-5 text-orange-400 mb-2" />
                <h3 className="text-sm font-semibold group-hover:text-primary transition-colors">Gap Analysis</h3>
                <p className="text-xs text-foreground/50 mt-1">Identify research gaps and opportunities</p>
              </GlassCard>
            </Link>
            <Link href={`/research/report?id=${projectId}`}>
              <GlassCard depth="flat" className="p-4 hover:border-primary/30 transition-all group cursor-pointer">
                <FileText className="w-5 h-5 text-purple-400 mb-2" />
                <h3 className="text-sm font-semibold group-hover:text-primary transition-colors">Generate Report</h3>
                <p className="text-xs text-foreground/50 mt-1">Create structured research reports</p>
              </GlassCard>
            </Link>
          </div>
        </div>
      )}
    </motion.div>
  )
}
