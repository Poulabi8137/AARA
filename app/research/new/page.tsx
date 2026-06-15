'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Sparkles, FileText, Search, Layers } from 'lucide-react'
import { motion } from 'framer-motion'
import { GlassCard } from '@/components/ui/glass-card'
import { Button } from '@/components/ui/button'

const presetTopics = [
  { icon: Sparkles, title: 'AI & Machine Learning', desc: 'Latest advances in deep learning, transformers, and neural architectures', color: 'from-purple-500 to-pink-500' },
  { icon: FileText, title: 'Healthcare & Biomedicine', desc: 'Drug discovery, medical imaging, genomics, and personalized medicine', color: 'from-blue-500 to-cyan-500' },
  { icon: Search, title: 'Climate & Sustainability', desc: 'Climate modeling, carbon capture, renewable energy, and ESG', color: 'from-green-500 to-emerald-500' },
  { icon: Layers, title: 'Computer Science', desc: 'Distributed systems, cryptography, programming languages, and HCI', color: 'from-orange-500 to-yellow-500' },
]

export default function NewResearchPage() {
  const router = useRouter()
  const [query, setQuery] = useState('')
  const [objective, setObjective] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    setIsSubmitting(true)
    try {
      const tokenRes = await fetch('/api/auth/session')
      const tokenData = await tokenRes.json()
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/projects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${tokenData?.token || ''}`,
        },
        body: JSON.stringify({
          title: query,
          description: objective,
        }),
      })
      if (res.ok) {
        const project = await res.json()
        router.push(`/research/${project.id}`)
      } else {
        alert('Failed to create research project. Is the backend running?')
      }
    } catch {
      alert('Failed to connect to backend. Creating a local project instead.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <motion.div className="max-w-3xl mx-auto space-y-8" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
      <div className="flex items-center gap-4">
        <Link href="/dashboard" className="p-2 rounded-lg hover:bg-white/5 transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">New Research Project</h1>
          <p className="text-sm text-foreground/50 mt-1">Define your research topic and let AI do the rest</p>
        </div>
      </div>

      <GlassCard depth="medium" className="p-6 space-y-6">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <label className="text-sm font-medium">Research Topic</label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., Applications of transformers in drug discovery"
              className="w-full px-4 py-3 rounded-xl bg-background/40 backdrop-blur-xl border border-border/50 text-sm focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Research Objective (optional)</label>
            <textarea
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              placeholder="What specific questions do you want answered?"
              rows={3}
              className="w-full px-4 py-3 rounded-xl bg-background/40 backdrop-blur-xl border border-border/50 text-sm focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all resize-none"
            />
          </div>

          <Button type="submit" disabled={!query.trim() || isSubmitting} className="w-full">
            {isSubmitting ? 'Creating Research Project...' : 'Start Research'}
          </Button>
        </form>
      </GlassCard>

      <div className="space-y-4">
        <h2 className="text-sm font-semibold text-foreground/50 uppercase tracking-wider">Quick Start Templates</h2>
        <div className="grid sm:grid-cols-2 gap-4">
          {presetTopics.map((topic, i) => {
            const Icon = topic.icon
            return (
              <button
                key={i}
                onClick={() => setQuery(topic.title + ' — ' + topic.desc.split(',')[0])}
                className="text-left p-4 rounded-xl border border-border/40 bg-background/40 backdrop-blur-xl hover:border-primary/30 transition-all group"
              >
                <div className={`w-8 h-8 rounded-lg bg-gradient-to-r ${topic.color} flex items-center justify-center mb-3`}>
                  <Icon className="w-4 h-4 text-white" />
                </div>
                <h3 className="text-sm font-semibold group-hover:text-primary transition-colors">{topic.title}</h3>
                <p className="text-xs text-foreground/50 mt-1">{topic.desc}</p>
              </button>
            )
          })}
        </div>
      </div>
    </motion.div>
  )
}
