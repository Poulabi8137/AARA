'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  Files,
  BookOpen,
  Search,
  Lightbulb,
  Quote,
  FileText,
  Activity,
  Settings,
  ChevronLeft,
  ChevronRight,
  Sparkles,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { href: '/dashboard', label: 'Overview', icon: LayoutDashboard },
  { href: '/research/papers', label: 'Papers', icon: Files },
  { href: '/research/literature', label: 'Literature', icon: BookOpen },
  { href: '/research/gaps', label: 'Gap Analysis', icon: Search },
  { href: '/research/directions', label: 'Directions', icon: Lightbulb },
  { href: '/research/citations', label: 'Citations', icon: Quote },
  { href: '/research/report', label: 'Report', icon: FileText },
  { href: '/research/monitoring', label: 'Monitoring', icon: Activity },
  { href: '/settings', label: 'Settings', icon: Settings },
]

interface AnimatedSidebarProps {
  className?: string
}

export function AnimatedSidebar({ className }: AnimatedSidebarProps) {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <motion.aside
      animate={{ width: collapsed ? 64 : 240 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className={cn(
        'relative h-full border-r border-border/50 bg-background/40 backdrop-blur-xl flex flex-col overflow-hidden',
        className
      )}
    >
      <div className="flex items-center justify-between p-4 border-b border-border/30">
        <AnimatePresence mode="wait">
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="flex items-center gap-2"
            >
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <span className="font-semibold text-sm">AARA OS</span>
            </motion.div>
          )}
        </AnimatePresence>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 rounded-lg hover:bg-muted/50 transition-colors text-foreground/50 hover:text-foreground"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          const Icon = item.icon
          return (
            <Link key={item.href} href={item.href} className="block">
              <motion.div
                whileHover={{ x: 2 }}
                whileTap={{ scale: 0.98 }}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                  isActive
                    ? 'bg-primary/10 text-primary border border-primary/20'
                    : 'text-foreground/60 hover:text-foreground hover:bg-muted/30 border border-transparent'
                )}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <AnimatePresence mode="wait">
                  {!collapsed && (
                    <motion.span
                      initial={{ opacity: 0, width: 0 }}
                      animate={{ opacity: 1, width: 'auto' }}
                      exit={{ opacity: 0, width: 0 }}
                      className="overflow-hidden whitespace-nowrap"
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>
              </motion.div>
            </Link>
          )
        })}
      </nav>

      <div className="p-3 border-t border-border/30">
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="px-3 py-2 rounded-lg bg-gradient-to-r from-primary/5 to-accent/5 border border-primary/10"
          >
            <p className="text-[10px] text-foreground/40 font-mono">v2.0.0 • Research OS</p>
          </motion.div>
        )}
      </div>
    </motion.aside>
  )
}
