'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion } from 'framer-motion'
import { ResearchFlow } from '@/components/research-flow'
import { ChevronRight, BookOpen, Search, Lightbulb, Quote, FileText, Sparkles } from 'lucide-react'

const researchModules = [
  { href: '/research/papers', label: 'Papers', icon: BookOpen },
  { href: '/research/literature', label: 'Literature', icon: Search },
  { href: '/research/gaps', label: 'Gap Analysis', icon: Search },
  { href: '/research/directions', label: 'Directions', icon: Lightbulb },
  { href: '/research/citations', label: 'Citations', icon: Quote },
  { href: '/research/report', label: 'Report', icon: FileText },
]

export default function ResearchLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  const currentModule = researchModules.find((m) => pathname.startsWith(m.href))

  return (
    <div className="min-h-[calc(100vh-56px)]">
      <div className="border-b border-border/40 bg-background/30 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="flex items-center gap-4 py-3">
            <Link href="/dashboard" className="text-xs text-foreground/40 hover:text-foreground/70 transition-colors">Dashboard</Link>
            <ChevronRight className="w-3 h-3 text-foreground/20" />
            {currentModule && (
              <>
                <span className="text-xs text-foreground/40">Research</span>
                <ChevronRight className="w-3 h-3 text-foreground/20" />
                <span className="text-xs text-foreground/70 font-medium">{currentModule.label}</span>
              </>
            )}
          </div>
          <div className="flex overflow-x-auto gap-1 pb-3 scrollbar-thin">
            {researchModules.map((mod) => {
              const isActive = pathname.startsWith(mod.href)
              const Icon = mod.icon
              return (
                <Link key={mod.href} href={mod.href}>
                  <motion.div
                    whileHover={{ y: -1 }}
                    whileTap={{ scale: 0.97 }}
                    className={`flex items-center gap-2 px-3.5 py-2 rounded-lg whitespace-nowrap text-xs font-medium transition-all duration-200 ${
                      isActive
                        ? 'bg-primary/10 text-primary border border-primary/20 shadow-sm'
                        : 'text-foreground/50 hover:text-foreground hover:bg-muted/30 border border-transparent'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {mod.label}
                  </motion.div>
                </Link>
              )
            })}
          </div>
        </div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="max-w-7xl mx-auto px-6 lg:px-8 py-6"
      >
        {children}
      </motion.div>
    </div>
  )
}
