'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { Activity, Zap, AlertCircle, CheckCircle, Network, Loader2 } from 'lucide-react'
import { GlassCard } from '@/components/ui/glass-card'
import { PageTransition, childVariants } from '@/components/page-transition'
import { AgentFlow } from '@/components/agent-flow'
import { apiClient } from '@/lib/api-client'

interface AgentExecution {
  id: string
  type: string
  status: string
  startTime: string | null
  endTime: string | null
  duration: string
  progress: number
}

const statusBadges: Record<string, string> = {
  completed: 'bg-green-500/10 text-green-400 border-green-500/20',
  running: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  failed: 'bg-red-500/10 text-red-400 border-red-500/20',
  pending: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
}

const statusIcons: Record<string, React.ReactNode> = {
  completed: <CheckCircle className="w-3.5 h-3.5" />,
  running: <Zap className="w-3.5 h-3.5 animate-pulse" />,
  failed: <AlertCircle className="w-3.5 h-3.5" />,
  pending: <Activity className="w-3.5 h-3.5" />,
}

export default function MonitoringPage() {
  const searchParams = useSearchParams()
  const executionId = searchParams.get('execution')

  const [executions, setExecutions] = useState<AgentExecution[]>([])
  const [stats, setStats] = useState({ completed: 0, running: 0, pending: 0, failed: 0 })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadExecutions = useCallback(async () => {
    try {
      const res = await apiClient.listExecutions()
      const data = res.data?.executions || res.data || []
      const items: AgentExecution[] = Array.isArray(data) ? data.map((e: any) => ({
        id: e.id,
        type: e.agent_name || e.type || 'Agent',
        status: e.execution_status || e.status || 'pending',
        startTime: e.start_time || e.startTime || null,
        endTime: e.end_time || e.endTime || null,
        duration: e.end_time && e.start_time
          ? `${Math.round((new Date(e.end_time).getTime() - new Date(e.start_time).getTime()) / 60000)}m`
          : 'Waiting',
        progress: e.execution_status === 'completed' ? 100 : e.execution_status === 'running' ? 65 : 0,
      })) : []
      setExecutions(items)
      setStats({
        completed: items.filter(e => e.status === 'completed').length,
        running: items.filter(e => e.status === 'running').length,
        pending: items.filter(e => e.status === 'pending').length,
        failed: items.filter(e => e.status === 'failed').length,
      })
      setError(null)
    } catch {
      if (executions.length === 0) {
        setError('Could not load execution data. Backend may be unavailable.')
      }
    }
    setIsLoading(false)
  }, [])

  useEffect(() => {
    loadExecutions()
    const interval = setInterval(loadExecutions, 10000)
    return () => clearInterval(interval)
  }, [loadExecutions])

  return (
    <PageTransition className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">Agent Monitoring</h1>
        <p className="text-sm text-foreground/50">Real-time monitoring of agent execution status</p>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-yellow-500/10 border border-yellow-500/20 text-xs text-yellow-400">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {executionId && (
        <div className="p-3 rounded-xl bg-primary/10 border border-primary/20 text-xs text-primary flex items-center gap-2">
          <Zap className="w-4 h-4" />
          Tracking execution: {executionId.slice(0, 8)}... — auto-refreshes every 10s
        </div>
      )}

      <motion.div className="grid md:grid-cols-4 gap-4" initial="hidden" animate="visible" variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.06 } } }}>
        {[
          { label: 'Completed', value: String(stats.completed), gradient: 'from-green-400 to-emerald-400' },
          { label: 'Running', value: String(stats.running), gradient: 'from-blue-400 to-cyan-400' },
          { label: 'Pending', value: String(stats.pending), gradient: 'from-yellow-400 to-orange-400' },
          { label: 'Failed', value: String(stats.failed), gradient: 'from-red-400 to-red-500' },
        ].map((stat, i) => (
          <motion.div key={i} variants={childVariants}>
            <GlassCard depth="flat" className="p-5">
              <p className="text-xs font-medium text-foreground/50">{stat.label}</p>
              <p className={`text-2xl font-bold mt-1 bg-gradient-to-r ${stat.gradient} bg-clip-text text-transparent`}>{stat.value}</p>
            </GlassCard>
          </motion.div>
        ))}
      </motion.div>

      <GlassCard depth="flat" className="p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Agent Pipeline</h2>
          <span className="text-[10px] text-foreground/40 font-mono">live</span>
        </div>
        <AgentFlow />
      </GlassCard>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </div>
      ) : (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold">Execution Details</h2>
          {executions.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-xs text-foreground/50">No executions yet. Run the agent workflow to see results here.</p>
            </div>
          ) : (
            <motion.div className="space-y-2" initial="hidden" animate="visible" variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.06 } } }}>
              {executions.slice(0, 20).map((agent) => (
                <motion.div key={agent.id} variants={childVariants}>
                  <GlassCard depth="flat" className="p-4">
                    <div className="space-y-2.5">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          {statusIcons[agent.status] || <Activity className="w-3.5 h-3.5" />}
                          <div>
                            <h3 className="text-xs font-semibold">{agent.type}</h3>
                            <p className="text-[10px] text-foreground/50">{agent.id.slice(0, 8)}...</p>
                          </div>
                        </div>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${statusBadges[agent.status] || statusBadges.pending}`}>
                          {agent.status.charAt(0).toUpperCase() + agent.status.slice(1)}
                        </span>
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] text-foreground/40">Progress</span>
                          <span className="text-[10px] font-semibold">{agent.progress}%</span>
                        </div>
                        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                          <div className="h-full bg-gradient-to-r from-primary to-accent rounded-full transition-all" style={{ width: `${agent.progress}%` }} />
                        </div>
                      </div>
                      <div className="text-[10px] text-foreground/40">Duration: {agent.duration}</div>
                    </div>
                  </GlassCard>
                </motion.div>
              ))}
            </motion.div>
          )}
        </div>
      )}

      <div className="flex gap-3">
        <button onClick={loadExecutions} className="px-5 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors shadow-lg shadow-primary/20">
          Refresh Now
        </button>
      </div>
    </PageTransition>
  )
}
