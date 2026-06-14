'use client'

import { motion } from 'framer-motion'

interface ThinkingStateProps {
  label?: string
  variant?: 'dots' | 'pulse' | 'ring'
}

export function ThinkingState({ label = 'AI is thinking', variant = 'dots' }: ThinkingStateProps) {
  if (variant === 'ring') {
    return (
      <div className="flex items-center gap-3">
        <div className="relative flex items-center justify-center w-6 h-6">
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-primary/30"
            animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          />
          <motion.div
            className="w-2 h-2 rounded-full bg-primary"
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 1, repeat: Infinity, ease: 'easeInOut' }}
          />
        </div>
        <span className="text-sm text-foreground/60 font-medium">{label}</span>
      </div>
    )
  }

  if (variant === 'pulse') {
    return (
      <div className="flex items-center gap-3">
        <motion.div
          className="w-2 h-2 rounded-full bg-primary"
          animate={{ scale: [1, 1.6, 1], opacity: [0.7, 1, 0.7] }}
          transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
        />
        <span className="text-sm text-foreground/60 font-medium">{label}</span>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-primary"
            animate={{ y: [0, -4, 0] }}
            transition={{
              duration: 0.8,
              repeat: Infinity,
              delay: i * 0.15,
              ease: 'easeInOut',
            }}
          />
        ))}
      </div>
      <span className="text-sm text-foreground/60 font-medium ml-1">{label}</span>
    </div>
  )
}
