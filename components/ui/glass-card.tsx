'use client'

import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import type { HTMLAttributes } from 'react'

interface GlassCardProps extends HTMLAttributes<HTMLDivElement> {
  hover?: boolean
  glow?: 'primary' | 'accent' | 'none'
  depth?: 'flat' | 'raised' | 'floating'
}

const depthStyles = {
  flat: 'shadow-sm',
  raised: 'shadow-lg shadow-black/5 dark:shadow-black/20',
  floating: 'shadow-xl shadow-primary/5 dark:shadow-primary/10 hover:shadow-2xl hover:shadow-primary/10',
}

const glowStyles = {
  primary: 'hover:border-primary/30',
  accent: 'hover:border-accent/30',
  none: '',
}

export function GlassCard({
  children,
  className,
  hover = true,
  glow = 'primary',
  depth = 'raised',
  ...props
}: GlassCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ type: 'spring', stiffness: 200, damping: 25 }}
      whileHover={hover ? { y: -2, scale: 1.005 } : undefined}
      className={cn(
        'rounded-xl border border-border/50 bg-background/60 dark:bg-white/[0.04] backdrop-blur-xl',
        'transition-all duration-300',
        depthStyles[depth],
        glowStyles[glow],
        hover && 'cursor-default',
        className
      )}
      {...props}
    >
      {children}
    </motion.div>
  )
}
