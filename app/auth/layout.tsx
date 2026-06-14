'use client'

import Link from 'next/link'
import { Sparkles } from 'lucide-react'
import { motion } from 'framer-motion'

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="hidden lg:flex lg:flex-col lg:justify-between lg:p-12 lg:relative lg:overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/90 via-primary/80 to-accent/90" />
        <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] rounded-full bg-white/5 blur-[80px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-accent/10 blur-[80px]" />

        <div className="relative z-10">
          <Link href="/" className="flex items-center gap-2 group">
            <motion.div whileHover={{ rotate: 180 }} transition={{ type: 'spring', stiffness: 300, damping: 15 }} className="w-9 h-9 rounded-xl bg-white/15 backdrop-blur flex items-center justify-center border border-white/10">
              <Sparkles className="w-4 h-4 text-white" />
            </motion.div>
            <span className="font-semibold text-lg text-white">AARA OS</span>
          </Link>
        </div>

        <div className="relative z-10 space-y-6 max-w-md">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-4xl font-bold text-white leading-tight"
          >
            Transform Your Research with Intelligent Agents
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-white/70 text-base leading-relaxed"
          >
            Discover papers, analyze gaps, and generate novel research directions powered by cutting-edge AI.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="flex gap-3"
          >
            {['Papers', 'Gaps', 'Directions', 'Reports'].map((tag) => (
              <span key={tag} className="px-3 py-1 rounded-full bg-white/10 text-white/60 text-[10px] font-medium border border-white/10">
                {tag}
              </span>
            ))}
          </motion.div>
        </div>

        <div className="relative z-10">
          <p className="text-white/40 text-xs">&copy; 2024 AARA OS</p>
        </div>
      </div>

      <div className="flex flex-col items-center justify-center px-4 py-12 bg-background">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-md"
        >
          <div className="lg:hidden flex justify-center mb-8">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <span className="font-semibold text-lg">AARA OS</span>
            </Link>
          </div>
          {children}
        </motion.div>
      </div>
    </div>
  )
}
