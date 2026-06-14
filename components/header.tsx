'use client'

import Link from 'next/link'
import { LogOut, Settings, Sparkles } from 'lucide-react'
import { useAuthStore } from '@/lib/store'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'

export function Header() {
  const { user, logout } = useAuthStore()
  const router = useRouter()

  const handleLogout = async () => {
    await logout()
    router.push('/')
  }

  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/60 backdrop-blur-2xl supports-[backdrop-filter]:bg-background/30"
    >
      <div className="container mx-auto px-4 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 group">
          <motion.div
            whileHover={{ rotate: 180, scale: 1.1 }}
            transition={{ type: 'spring', stiffness: 300, damping: 15 }}
            className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-lg shadow-primary/20"
          >
            <Sparkles className="w-3.5 h-3.5 text-white" />
          </motion.div>
          <span className="hidden sm:inline font-semibold text-sm tracking-tight">
            AARA <span className="text-foreground/40 font-normal">OS</span>
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-6">
          {user && (
            <>
              {['/dashboard', '/research/papers', '/settings'].map((href, i) => (
                <Link
                  key={href}
                  href={href}
                  className="text-xs font-medium text-foreground/50 hover:text-foreground transition-colors tracking-wide uppercase"
                >
                  {['Dashboard', 'Research', 'Settings'][i]}
                </Link>
              ))}
            </>
          )}
        </nav>

        <div className="flex items-center gap-3">
          {user ? (
            <div className="flex items-center gap-2">
              <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-full bg-muted/50 border border-border/30">
                <div className="w-5 h-5 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center">
                  <span className="text-[9px] text-white font-bold">
                    {user.name?.charAt(0) || 'U'}
                  </span>
                </div>
                <span className="text-xs text-foreground/70 font-medium">{user.name}</span>
              </div>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => router.push('/settings')}
                className="p-1.5 rounded-lg hover:bg-muted/50 transition-colors"
              >
                <Settings className="w-4 h-4 text-foreground/50" />
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleLogout}
                className="p-1.5 rounded-lg hover:bg-destructive/10 transition-colors"
              >
                <LogOut className="w-4 h-4 text-destructive/70" />
              </motion.button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                href="/auth/login"
                className="px-3 py-1.5 text-xs font-medium text-foreground/60 hover:text-foreground transition-colors"
              >
                Sign In
              </Link>
              <Link
                href="/auth/signup"
                className="px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors shadow-lg shadow-primary/20"
              >
                Get Started
              </Link>
            </div>
          )}
        </div>
      </div>
    </motion.header>
  )
}
