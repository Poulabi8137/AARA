'use client'

import { motion } from 'framer-motion'
import { Activity, Zap, AlertCircle, CheckCircle, Network } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ScatterChart, Scatter } from 'recharts'
import { GlassCard } from '@/components/ui/glass-card'
import { PageTransition, childVariants } from '@/components/page-transition'
import { AgentFlow } from '@/components/agent-flow'

const agentExecutions = [
  { id: '1', type: 'Planner', status: 'completed', startTime: '09:00', endTime: '09:05', duration: '5m', progress: 100 },
  { id: '2', type: 'Retriever', status: 'completed', startTime: '09:05', endTime: '09:35', duration: '30m', progress: 100 },
  { id: '3', type: 'Summarizer', status: 'running', startTime: '09:35', endTime: null, duration: '12m 45s', progress: 65 },
  { id: '4', type: 'Analyzer', status: 'pending', startTime: null, endTime: null, duration: 'Waiting', progress: 0 },
]

const timelineData = [
  { time: '09:00', Planner: 1, Retriever: 0, Summarizer: 0, Analyzer: 0 },
  { time: '09:05', Planner: 0, Retriever: 1, Summarizer: 0, Analyzer: 0 },
  { time: '09:10', Planner: 0, Retriever: 1, Summarizer: 0, Analyzer: 0 },
  { time: '09:15', Planner: 0, Retriever: 1, Summarizer: 0, Analyzer: 0 },
  { time: '09:20', Planner: 0, Retriever: 1, Summarizer: 0, Analyzer: 0 },
  { time: '09:25', Planner: 0, Retriever: 1, Summarizer: 0, Analyzer: 0 },
  { time: '09:30', Planner: 0, Retriever: 1, Summarizer: 0, Analyzer: 0 },
  { time: '09:35', Planner: 0, Retriever: 0, Summarizer: 1, Analyzer: 0 },
  { time: '09:40', Planner: 0, Retriever: 0, Summarizer: 1, Analyzer: 0 },
  { time: '09:45', Planner: 0, Retriever: 0, Summarizer: 1, Analyzer: 0 },
]

const agentCommunications = [
  { agent1: 'Planner', agent2: 'Retriever', messages: 5, weight: 3 },
  { agent1: 'Retriever', agent2: 'Summarizer', messages: 12, weight: 5 },
  { agent1: 'Summarizer', agent2: 'Analyzer', messages: 8, weight: 4 },
  { agent1: 'Analyzer', agent2: 'Planner', messages: 2, weight: 1 },
]

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
  return (
    <PageTransition className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">Agent Monitoring</h1>
        <p className="text-sm text-foreground/50">Real-time monitoring of agent execution with Timeline, Graph, and Logs visualization</p>
      </div>

      <motion.div className="grid md:grid-cols-4 gap-4" initial="hidden" animate="visible" variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.06 } } }}>
        {[
          { label: 'Completed', value: '2', gradient: 'from-green-400 to-emerald-400' },
          { label: 'Running', value: '1', gradient: 'from-blue-400 to-cyan-400' },
          { label: 'Pending', value: '1', gradient: 'from-yellow-400 to-orange-400' },
          { label: 'Failed', value: '0', gradient: 'from-red-400 to-red-500' },
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

      <div className="space-y-3">
        <h2 className="text-sm font-semibold">Execution Details</h2>
        <motion.div className="space-y-2" initial="hidden" animate="visible" variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.06 } } }}>
          {agentExecutions.map((agent) => (
            <motion.div key={agent.id} variants={childVariants}>
              <GlassCard depth="flat" className="p-4">
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      {statusIcons[agent.status]}
                      <div>
                        <h3 className="text-xs font-semibold">{agent.type} Agent</h3>
                        <p className="text-[10px] text-foreground/50">
                          {agent.startTime} {agent.endTime ? `→ ${agent.endTime}` : ''}
                        </p>
                      </div>
                    </div>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${statusBadges[agent.status]}`}>
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
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <GlassCard depth="flat" className="p-5 space-y-4">
          <h3 className="text-xs font-semibold">Agent Communication Network</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis type="number" dataKey="x" hide />
                <YAxis type="number" dataKey="y" hide />
                <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ background: 'oklch(0.16 0 0)', border: '1px solid oklch(1 0 0 / 0.1)', borderRadius: '8px', fontSize: '11px' }} />
                <Scatter name="Interactions" data={[{ x: 1, y: 5, agent: 'Planner → Retriever' }, { x: 2, y: 12, agent: 'Retriever → Summarizer' }, { x: 3, y: 8, agent: 'Summarizer → Analyzer' }, { x: 4, y: 2, agent: 'Analyzer → Planner' }]} fill="#6366f1" />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-1.5">
            {agentCommunications.map((comm, idx) => (
              <div key={idx} className="p-2 rounded-lg bg-muted/30 border border-border/30">
                <p className="text-[10px] text-foreground/50 font-mono">{comm.agent1}</p>
                <p className="text-[10px] text-primary font-semibold">→ {comm.messages} msgs</p>
              </div>
            ))}
          </div>
        </GlassCard>

        <GlassCard depth="flat" className="p-5 space-y-4">
          <h3 className="text-xs font-semibold">Execution Timeline</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={timelineData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.4)' }} />
                <YAxis tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.4)' }} />
                <Tooltip contentStyle={{ background: 'oklch(0.16 0 0)', border: '1px solid oklch(1 0 0 / 0.1)', borderRadius: '8px', fontSize: '11px' }} />
                <Bar dataKey="Planner" stackId="a" fill="#6366f1" radius={[2, 2, 0, 0]} />
                <Bar dataKey="Retriever" stackId="a" fill="#8b5cf6" radius={[2, 2, 0, 0]} />
                <Bar dataKey="Summarizer" stackId="a" fill="#ec4899" radius={[2, 2, 0, 0]} />
                <Bar dataKey="Analyzer" stackId="a" fill="#14b8a6" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>
      </div>

      <GlassCard depth="flat" className="p-5 space-y-3">
        <h2 className="text-sm font-semibold">Execution Logs</h2>
        <div className="p-4 rounded-xl bg-muted/30 border border-border/30 font-mono text-[10px] text-foreground/60 space-y-1 max-h-48 overflow-y-auto scrollbar-thin">
          <div className="text-green-400/80">[09:00:00] Planner Agent started</div>
          <div className="text-green-400/80">[09:00:15] Parsed research topic: Deep Learning in Healthcare</div>
          <div className="text-green-400/80">[09:00:45] Generated 5 search queries</div>
          <div className="text-green-400/80">[09:05:00] Planner Agent completed</div>
          <div className="text-blue-400/80">[09:05:00] Retriever Agent started</div>
          <div className="text-blue-400/80">[09:10:30] Retrieved 25 papers from ArXiv</div>
          <div className="text-blue-400/80">[09:15:45] Retrieved 32 papers from Scholar</div>
          <div className="text-blue-400/80">[09:20:00] Retrieved 18 papers from PubMed</div>
          <div className="text-blue-400/80">[09:35:00] Retriever Agent completed (75 papers)</div>
          <div className="text-yellow-400/80">[09:35:00] Summarizer Agent started</div>
          <div className="text-yellow-400/80">[09:40:00] Summarized 25 papers</div>
          <div className="text-yellow-400/80">[09:45:00] Summarized 50 papers (in progress...)</div>
        </div>
      </GlassCard>

      <div className="flex gap-3">
        <button className="px-5 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors shadow-lg shadow-primary/20">
          Pause Execution
        </button>
        <button className="px-5 py-2 rounded-xl border border-border/50 text-foreground/70 text-xs font-medium hover:bg-muted/30 transition-colors">
          Download Logs
        </button>
        <button className="px-5 py-2 rounded-xl border border-border/50 text-foreground/70 text-xs font-medium hover:bg-muted/30 transition-colors">
          Clear Logs
        </button>
      </div>
    </PageTransition>
  )
}
