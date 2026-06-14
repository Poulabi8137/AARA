'use client'

import { useMemo, useCallback } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { CheckCircle, Zap, AlertCircle, Clock } from 'lucide-react'

const statusIcons = {
  completed: CheckCircle,
  running: Zap,
  failed: AlertCircle,
  pending: Clock,
}

const statusColors = {
  completed: 'text-green-400 border-green-500/30 bg-green-500/10',
  running: 'text-blue-400 border-blue-500/30 bg-blue-500/10',
  failed: 'text-red-400 border-red-500/30 bg-red-500/10',
  pending: 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10',
}

function AgentNode({ data }: NodeProps) {
  const StatusIcon = statusIcons[data.status as keyof typeof statusIcons]
  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 200, damping: 20 }}
      className={cn(
        'px-4 py-3 rounded-xl border backdrop-blur-xl min-w-[160px]',
        statusColors[data.status as keyof typeof statusColors] || 'border-border/50 bg-background/60'
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-primary/50 !w-2 !h-2" />
      <div className="flex items-center gap-2">
        {StatusIcon && <StatusIcon className="w-4 h-4" />}
        <span className="text-sm font-semibold">{data.label}</span>
      </div>
      {data.progress !== undefined && (
        <div className="mt-2 h-1 rounded-full bg-muted overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-primary to-accent rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${data.progress}%` }}
            transition={{ duration: 1, ease: 'easeOut' }}
          />
        </div>
      )}
      {data.description && (
        <p className="text-[10px] text-foreground/50 mt-1">{data.description}</p>
      )}
      <Handle type="source" position={Position.Right} className="!bg-primary/50 !w-2 !h-2" />
    </motion.div>
  )
}

const nodeTypes = { agent: AgentNode }

const defaultNodes: Node[] = [
  { id: 'planner', type: 'agent', position: { x: 0, y: 100 }, data: { label: 'Planner', status: 'completed', progress: 100, description: 'Research plan' } },
  { id: 'retriever', type: 'agent', position: { x: 220, y: 0 }, data: { label: 'Retriever', status: 'completed', progress: 100, description: '75 papers' } },
  { id: 'summarizer', type: 'agent', position: { x: 220, y: 200 }, data: { label: 'Summarizer', status: 'running', progress: 65, description: 'Synthesizing...' } },
  { id: 'analyzer', type: 'agent', position: { x: 440, y: 0 }, data: { label: 'Analyzer', status: 'pending', progress: 0, description: 'Gap analysis' } },
  { id: 'generator', type: 'agent', position: { x: 440, y: 200 }, data: { label: 'Generator', status: 'pending', progress: 0, description: 'Directions' } },
]

const defaultEdges: Edge[] = [
  { id: 'e-planner-retriever', source: 'planner', target: 'retriever', animated: true, style: { stroke: 'rgba(99,102,241,0.5)', strokeWidth: 2 } },
  { id: 'e-planner-summarizer', source: 'planner', target: 'summarizer', animated: true, style: { stroke: 'rgba(99,102,241,0.5)', strokeWidth: 2 } },
  { id: 'e-retriever-analyzer', source: 'retriever', target: 'analyzer', animated: true, style: { stroke: 'rgba(168,85,247,0.5)', strokeWidth: 2 } },
  { id: 'e-summarizer-generator', source: 'summarizer', target: 'generator', animated: true, style: { stroke: 'rgba(168,85,247,0.5)', strokeWidth: 2 } },
]

export function AgentFlow({ className }: { className?: string }) {
  const [nodes, setNodes, onNodesChange] = useNodesState(defaultNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(defaultEdges)

  return (
    <div className={cn('h-[300px] rounded-xl overflow-hidden border border-border/50', className)}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
        proOptions={{ hideAttribution: true }}
      >
        <Background color="rgba(255,255,255,0.03)" gap={20} />
        <Controls className="!bg-background/80 !backdrop-blur-xl !border !border-border/50 !rounded-lg" />
        <MiniMap
          className="!bg-background/80 !backdrop-blur-xl !border !border-border/50 !rounded-lg"
          nodeColor={() => 'rgba(99,102,241,0.3)'}
          maskColor="rgba(0,0,0,0.3)"
        />
      </ReactFlow>
    </div>
  )
}
