'use client'

import { Suspense, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { Mail, Lock, ArrowRight, Loader2 } from 'lucide-react'
import { useAuthStore } from '@/lib/store'
import { motion } from 'framer-motion'

function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const login = useAuthStore((state) => state.login)
  const clearError = useAuthStore((state) => state.clearError)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formData, setFormData] = useState({ email: '', password: '' })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
    setError(null)
    clearError()
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)
    try {
      await login(formData.email, formData.password)
      const redirect = searchParams.get('redirect') || '/dashboard'
      router.push(redirect)
    } catch (err: unknown) {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || (err instanceof Error ? err.message : 'Login failed'))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="text-center space-y-1.5">
        <h1 className="text-2xl font-bold tracking-tight">Welcome Back</h1>
        <p className="text-sm text-foreground/50">Sign in to continue your research</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <label htmlFor="email" className="text-xs font-medium text-foreground/70">Email</label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/30" />
            <input
              id="email" name="email" type="email" placeholder="your@email.com"
              value={formData.email} onChange={handleChange} required
              className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-muted/50 border border-border/50 text-sm text-foreground placeholder:text-foreground/30 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <label htmlFor="password" className="text-xs font-medium text-foreground/70">Password</label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/30" />
            <input
              id="password" name="password" type="password" placeholder="••••••••"
              value={formData.password} onChange={handleChange} required
              className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-muted/50 border border-border/50 text-sm text-foreground placeholder:text-foreground/30 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all"
            />
          </div>
        </div>

        {error && (
          <motion.div initial={{ opacity: 0, y: -5 }} animate={{ opacity: 1, y: 0 }} className="p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-xs text-destructive">
            {error}
          </motion.div>
        )}

        <motion.button
          whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}
          type="submit" disabled={isLoading}
          className="w-full py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-semibold shadow-lg shadow-primary/20 hover:shadow-xl hover:shadow-primary/30 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Signing in...</>
          ) : (
            <><ArrowRight className="w-4 h-4" /> Sign In</>
          )}
        </motion.button>
      </form>

      <div className="relative">
        <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-border/50" /></div>
        <div className="relative flex justify-center text-xs"><span className="px-2 bg-background text-foreground/40">New to AARA?</span></div>
      </div>

      <Link
        href="/auth/signup"
        className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl border border-border/50 text-foreground/70 text-sm font-medium hover:bg-muted/30 transition-colors"
      >
        Create Account <ArrowRight className="w-4 h-4" />
      </Link>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="text-center text-sm text-foreground/50 py-12">Loading...</div>}>
      <LoginForm />
    </Suspense>
  )
}
