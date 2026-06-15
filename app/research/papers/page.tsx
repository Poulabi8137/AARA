'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { Search, Filter, Download, Star, ExternalLink, ChevronDown, Loader2, AlertTriangle } from 'lucide-react'
import { motion } from 'framer-motion'
import { GlassCard } from '@/components/ui/glass-card'
import { PageTransition, childVariants } from '@/components/page-transition'
import { SkeletonCard } from '@/components/ui/skeleton'
import { fetchPapers } from '@/lib/api/research-api'
import type { Paper } from '@/lib/types'

const mockPapers: Paper[] = [
  { id: '1', title: 'Deep Learning Architectures for Medical Image Analysis', authors: ['Smith, J.', 'Johnson, A.', 'Williams, B.'], year: 2024, citations: 342, source: 'arxiv', doi: '10.1234/example', summary: 'A comprehensive review of state-of-the-art deep learning models used for medical image analysis...', abstract: '', relevanceScore: 95 },
  { id: '2', title: 'Transformers in Natural Language Understanding', authors: ['Brown, C.', 'Davis, D.'], year: 2023, citations: 1205, source: 'scholar', doi: '10.5678/example', summary: 'Explores the evolution and effectiveness of transformer architectures in NLP tasks...', abstract: '', relevanceScore: 87 },
  { id: '3', title: 'Federated Learning for Privacy-Preserving AI', authors: ['Miller, E.', 'Wilson, F.'], year: 2024, citations: 156, source: 'pubmed', doi: '10.9101/example', summary: 'Investigation into federated learning approaches that maintain data privacy...', abstract: '', relevanceScore: 82 },
]

export default function PapersPage() {
  const params = useParams()
  const projectId = params?.id as string

  const [papers, setPapers] = useState<Paper[]>(mockPapers)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<'relevance' | 'citations' | 'year'>('relevance')
  const [starred, setStarred] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!projectId) {
      setIsLoading(false)
      return
    }
    const load = async () => {
      setIsLoading(true)
      const result = await fetchPapers(projectId)
      if (result.data && !result.isMock) {
        setPapers(result.data)
      }
      if (result.error) {
        setError(result.error)
      }
      setIsLoading(false)
    }
    load()
  }, [projectId])

  const toggleStar = (id: string) => {
    const next = new Set(starred)
    next.has(id) ? next.delete(id) : next.add(id)
    setStarred(next)
  }

  const filtered = papers.filter(p =>
    p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.authors.some(a => a.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  const sorted = [...filtered].sort((a, b) => {
    if (sortBy === 'citations') return (b.citations ?? 0) - (a.citations ?? 0)
    if (sortBy === 'year') return (b.year ?? 0) - (a.year ?? 0)
    return (b.relevanceScore ?? 0) - (a.relevanceScore ?? 0)
  })

  return (
    <PageTransition className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">Papers Repository</h1>
        <p className="text-sm text-foreground/50">Manage and organize research papers for your project</p>
      </div>

      <div className="flex flex-col md:flex-row gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/30" />
          <input
            type="text" placeholder="Search papers by title or author..."
            value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-xl bg-background/40 backdrop-blur-xl border border-border/50 text-sm placeholder:text-foreground/30 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all"
          />
        </div>
        <div className="flex gap-2">
          <div className="relative">
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)}
              className="appearance-none px-3 py-2 rounded-xl bg-background/40 backdrop-blur-xl border border-border/50 text-sm text-foreground focus:outline-none focus:border-primary/50 pr-7 cursor-pointer"
            >
              <option value="relevance">Relevance</option>
              <option value="citations">Citations</option>
              <option value="year">Year</option>
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-foreground/30 pointer-events-none" />
          </div>
          <button className="p-2 rounded-xl bg-background/40 backdrop-blur-xl border border-border/50 text-foreground/50 hover:text-foreground transition-colors">
            <Filter className="w-4 h-4" />
          </button>
          <button className="p-2 rounded-xl bg-background/40 backdrop-blur-xl border border-border/50 text-foreground/50 hover:text-foreground transition-colors">
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-400">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => <SkeletonCard key={i} />)}
        </div>
      ) : sorted.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-sm text-foreground/50">No papers found{searchQuery ? ' matching your search' : ''}.</p>
        </div>
      ) : (
        <motion.div className="space-y-3" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ staggerChildren: 0.06 }}>
          {sorted.map((paper) => (
            <motion.div key={paper.id} variants={childVariants}>
              <GlassCard depth="flat" className="p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0 space-y-2">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-semibold truncate">{paper.title}</h3>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-muted/50 text-foreground/40 border border-border/30 shrink-0">{paper.source}</span>
                    </div>
                    <p className="text-xs text-foreground/50">{paper.authors.join(', ')}</p>
                    <p className="text-xs text-foreground/60 leading-relaxed">{paper.summary}</p>
                    <div className="flex flex-wrap gap-3 text-[10px] text-foreground/40">
                      <span>Year: {paper.year}</span>
                      <span>Citations: {paper.citations}</span>
                      {paper.doi && <span className="text-primary/70 hover:text-primary cursor-pointer">DOI: {paper.doi}</span>}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-foreground/40">Relevance</span>
                      <div className="flex-1 max-w-[120px] h-1 rounded-full bg-muted overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-primary to-accent rounded-full" style={{ width: `${paper.relevanceScore ?? 0}%` }} />
                      </div>
                      <span className="text-[10px] font-semibold text-primary">{paper.relevanceScore ?? 0}%</span>
                    </div>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <button onClick={() => toggleStar(paper.id)} className="p-1.5 rounded-lg hover:bg-muted/50 transition-colors">
                      <Star className={`w-4 h-4 ${starred.has(paper.id) ? 'fill-yellow-400 text-yellow-400' : 'text-foreground/30'}`} />
                    </button>
                    <button className="p-1.5 rounded-lg hover:bg-muted/50 transition-colors">
                      <ExternalLink className="w-4 h-4 text-foreground/30" />
                    </button>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </motion.div>
      )}
    </PageTransition>
  )
}
