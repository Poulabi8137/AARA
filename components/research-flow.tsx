'use client'

import {
  ReactFlow,
  Background,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
  MarkerType,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { BookOpen, Search, Lightbulb, Quote, FileText } from 'lucide-react'

const moduleIcons: Record<string, React.ElementType> = {
  papers: BookOpen,
  literature: Search,
  gaps: Search,
  directions: Lightbulb,
  citations: Quote,
  report: FileText,
}

const moduleGradients: Record<string, string> = {
  papers: 'from-blue-500/20 to-cyan-500/20 border-blue-500/20',
  literature: 'from-purple-500/20 to-pink-500/20 border-purple-500/20',
  gaps: 'from-orange-500/20 to-yellow-500/20 border-orange-500/20',
  directions: 'from-green-500/20 to-emerald-500/20 border-green-500/20',
  citations: 'from-indigo-500/20 to-violet-500/20 border-indigo-500/20',
  report: 'from-rose-500/20 to-red-500/20 border-rose-500/20',
}

function ModuleNode({ data: rawData }: NodeProps) {
  const data = rawData as { label?: string; moduleId?: string }
  const Icon = moduleIcons[data.moduleId as keyof typeof moduleIcons]
  return (
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      whileHover={{ scale: 1.05 }}
      className={cn(
        'px-5 py-4 rounded-xl border backdrop-blur-xl min-w-[180px] cursor-pointer',
        'bg-background/60 dark:bg-white/[0.04]',
        moduleGradients[data.moduleId as keyof typeof moduleGradients] || 'border-border/50'
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-primary/50 !w-2 !h-2" />
      <div className="flex flex-col items-center gap-2 text-center">
        {Icon && <Icon className="w-5 h-5 text-foreground/70" />}
        <span className="text-xs font-semibold text-foreground">{data.label}</span>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-primary/50 !w-2 !h-2" />
    </motion.div>
  )
}

const nodeTypes = { module: ModuleNode }

const researchNodes: Node[] = [
  { id: 'papers', type: 'module', position: { x: 0, y: 0 }, data: { label: 'Papers', moduleId: 'papers' } },
  { id: 'literature', type: 'module', position: { x: 220, y: 0 }, data: { label: 'Literature', moduleId: 'literature' } },
  { id: 'gaps', type: 'module', position: { x: 440, y: 0 }, data: { label: 'Gap Analysis', moduleId: 'gaps' } },
  { id: 'directions', type: 'module', position: { x: 660, y: 0 }, data: { label: 'Directions', moduleId: 'directions' } },
  { id: 'citations', type: 'module', position: { x: 220, y: 120 }, data: { label: 'Citations', moduleId: 'citations' } },
  { id: 'report', type: 'module', position: { x: 440, y: 120 }, data: { label: 'Report', moduleId: 'report' } },
]

const researchEdges: Edge[] = [
  { id: 'e-papers-lit', source: 'papers', target: 'literature', animated: true, style: { stroke: 'rgba(99,102,241,0.4)', strokeWidth: 1.5 }, markerEnd: { type: MarkerType.ArrowClosed, color: 'rgba(99,102,241,0.4)' } },
  { id: 'e-lit-gaps', source: 'literature', target: 'gaps', animated: true, style: { stroke: 'rgba(99,102,241,0.4)', strokeWidth: 1.5 }, markerEnd: { type: MarkerType.ArrowClosed, color: 'rgba(99,102,241,0.4)' } },
  { id: 'e-gaps-dir', source: 'gaps', target: 'directions', animated: true, style: { stroke: 'rgba(99,102,241,0.4)', strokeWidth: 1.5 }, markerEnd: { type: MarkerType.ArrowClosed, color: 'rgba(99,102,241,0.4)' } },
  { id: 'e-papers-cite', source: 'papers', target: 'citations', animated: true, style: { stroke: 'rgba(168,85,247,0.3)', strokeWidth: 1.5 }, markerEnd: { type: MarkerType.ArrowClosed, color: 'rgba(168,85,247,0.3)' } },
  { id: 'e-dir-report', source: 'directions', target: 'report', animated: true, style: { stroke: 'rgba(168,85,247,0.3)', strokeWidth: 1.5 }, markerEnd: { type: MarkerType.ArrowClosed, color: 'rgba(168,85,247,0.3)' } },
]

export function ResearchFlow({ className }: { className?: string }) {
  const [nodes, , onNodesChange] = useNodesState(researchNodes)
  const [edges, , onEdgesChange] = useEdgesState(researchEdges)

  return (
    <div className={cn('h-[200px] rounded-xl overflow-hidden border border-border/50', className)}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background color="rgba(255,255,255,0.02)" gap={16} />
      </ReactFlow>
    </div>
  )
}
