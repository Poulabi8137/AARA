'use client'

import Link from 'next/link'
import { Header } from '@/components/header'
import { ArrowRight, Sparkles, BookOpen, Zap, Shield, TrendingUp, Layers, Network } from 'lucide-react'
import { motion } from 'framer-motion'
import { AgentFlow } from '@/components/agent-flow'

const features = [
  {
    icon: BookOpen, title: 'Literature Intelligence',
    description: 'AI-powered research paper analysis and discovery across millions of academic sources.',
    gradient: 'from-blue-500/20 to-cyan-500/20',
  },
  {
    icon: Zap, title: 'Instant Synthesis',
    description: 'Automatically synthesize research themes and generate comprehensive literature reviews.',
    gradient: 'from-purple-500/20 to-pink-500/20',
  },
  {
    icon: TrendingUp, title: 'Gap Discovery',
    description: 'Identify research gaps with evidence-backed analysis and confidence scores.',
    gradient: 'from-orange-500/20 to-yellow-500/20',
  },
  {
    icon: Layers, title: 'Novel Directions',
    description: 'Generate innovative research directions grounded in existing literature.',
    gradient: 'from-green-500/20 to-emerald-500/20',
  },
  {
    icon: Shield, title: 'Explainable AI',
    description: 'Transparent agent reasoning with source citations and evidence panels.',
    gradient: 'from-indigo-500/20 to-violet-500/20',
  },
  {
    icon: Network, title: 'Agent Pipeline',
    description: 'Visual multi-agent workflow with real-time progress tracking.',
    gradient: 'from-rose-500/20 to-red-500/20',
  },
]

const stagger = { hidden: { opacity: 0 }, visible: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.15 } } }
const fadeUp = { hidden: { opacity: 0, y: 16 }, visible: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 200, damping: 25 } } }

export default function Page() {
  return (
    <>
      <Header />
      <main className="min-h-screen">
        <section className="relative overflow-hidden pt-20 pb-32 px-4">
          <div className="absolute inset-0 -z-10">
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1200px] h-[800px] bg-gradient-to-b from-primary/15 via-accent/8 to-transparent rounded-full blur-[120px]" />
            <div className="absolute top-[30%] right-[10%] w-64 h-64 rounded-full bg-accent/5 blur-[80px]" />
            <div className="absolute top-[20%] left-[5%] w-48 h-48 rounded-full bg-primary/5 blur-[60px]" />
          </div>

          <div className="container mx-auto max-w-6xl">
            <motion.div className="text-center space-y-8" variants={stagger} initial="hidden" animate="visible">
              <motion.div variants={fadeUp} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full glass text-xs font-medium">
                <Sparkles className="w-3.5 h-3.5 text-primary" />
                <span className="text-foreground/70">Powered by Intelligent Agents</span>
              </motion.div>

              <motion.h1 variants={fadeUp} className="text-5xl md:text-7xl font-bold leading-[1.05] tracking-tight">
                Research Redefined by{' '}
                <span className="text-gradient">Intelligent Agents</span>
              </motion.h1>

              <motion.p variants={fadeUp} className="text-lg md:text-xl text-foreground/60 max-w-3xl mx-auto leading-relaxed">
                AARA OS harnesses advanced agents to discover papers, analyze research gaps, and generate novel research directions with explainable AI.
              </motion.p>

              <motion.div variants={fadeUp} className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
                <Link
                  href="/auth/signup"
                  className="group relative px-8 py-3.5 rounded-xl bg-primary text-primary-foreground font-semibold text-sm overflow-hidden shadow-xl shadow-primary/20 hover:shadow-2xl hover:shadow-primary/30 transition-shadow"
                >
                  <span className="relative z-10 flex items-center gap-2">
                    Start Your Research <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </span>
                  <div className="absolute inset-0 bg-gradient-to-r from-primary to-accent opacity-0 group-hover:opacity-100 transition-opacity" />
                </Link>
                <Link
                  href="#features"
                  className="px-8 py-3.5 rounded-xl glass text-foreground/70 font-medium text-sm hover:text-foreground transition-colors"
                >
                  Explore Features
                </Link>
              </motion.div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6, duration: 0.6 }}
              className="mt-20 relative"
            >
              <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-accent/5 to-transparent rounded-2xl blur-3xl" />
              <AgentFlow className="relative rounded-2xl border border-border/40 shadow-2xl shadow-primary/5" />
            </motion.div>
          </div>
        </section>

        <section id="features" className="py-24 px-4 border-t border-border/40">
          <div className="container mx-auto max-w-6xl">
            <motion.div className="text-center mb-16 space-y-4" variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true }}>
              <motion.h2 variants={fadeUp} className="text-4xl md:text-5xl font-bold tracking-tight">
                Everything you need
              </motion.h2>
              <motion.p variants={fadeUp} className="text-lg text-foreground/60 max-w-2xl mx-auto">
                A complete research operating system powered by collaborative AI agents
              </motion.p>
            </motion.div>

            <motion.div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5" variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true }}>
              {features.map((feature, i) => {
                const Icon = feature.icon
                return (
                  <motion.div
                    key={i} variants={fadeUp}
                    className="group relative p-6 rounded-xl border border-border/40 bg-background/40 backdrop-blur-xl hover:bg-background/60 transition-all duration-300"
                  >
                    <div className={`absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-gradient-to-br ${feature.gradient}`} />
                    <div className="relative z-10">
                      <div className="w-10 h-10 rounded-lg bg-primary/10 backdrop-blur flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                        <Icon className="w-5 h-5 text-primary" />
                      </div>
                      <h3 className="text-base font-semibold mb-2">{feature.title}</h3>
                      <p className="text-sm text-foreground/60 leading-relaxed">{feature.description}</p>
                    </div>
                  </motion.div>
                )
              })}
            </motion.div>
          </div>
        </section>

        <section className="py-24 px-4 border-t border-border/40">
          <div className="container mx-auto max-w-4xl">
            <motion.div className="text-center mb-16 space-y-4" variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true }}>
              <motion.h2 variants={fadeUp} className="text-4xl md:text-5xl font-bold tracking-tight">Research Pipeline</motion.h2>
              <motion.p variants={fadeUp} className="text-lg text-foreground/60">A multi-agent workflow that transforms ideas into insights</motion.p>
            </motion.div>

            <motion.div className="space-y-3" variants={stagger} initial="hidden" whileInView="visible" viewport={{ once: true }}>
              {[
                ['Research Input', 'Define your research question or topic'],
                ['Planner Agent', 'Creates a structured research plan with search queries'],
                ['Retriever Agent', 'Discovers and fetches relevant papers from multiple sources'],
                ['Summarizer Agent', 'Synthesizes key findings and identifies themes'],
                ['Analyzer Agent', 'Identifies research gaps and opportunities'],
                ['Generator Agent', 'Produces novel research directions and reports'],
              ].map(([step, desc], i) => (
                <motion.div key={i} variants={fadeUp} className="flex items-center gap-4 group">
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-accent text-white flex items-center justify-center font-bold text-xs shadow-lg shadow-primary/20 flex-shrink-0">
                    {i + 1}
                  </div>
                  <div className="flex-1 p-4 rounded-xl glass border border-border/40 group-hover:border-primary/20 transition-colors">
                    <p className="font-semibold text-sm">{step}</p>
                    <p className="text-xs text-foreground/50 mt-0.5">{desc}</p>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        <section className="py-24 px-4 border-t border-border/40">
          <div className="container mx-auto max-w-2xl text-center space-y-8">
            <h2 className="text-4xl font-bold tracking-tight">Ready to transform your research?</h2>
            <p className="text-lg text-foreground/60">Start discovering insights and generating novel research directions today.</p>
            <Link
              href="/auth/signup"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-primary text-primary-foreground font-semibold text-sm shadow-xl shadow-primary/20 hover:shadow-2xl hover:shadow-primary/30 transition-all"
            >
              Get Started for Free <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </section>

        <footer className="border-t border-border/40 py-12 px-4">
          <div className="container mx-auto max-w-6xl">
            <div className="grid md:grid-cols-4 gap-8 mb-8">
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
                    <Sparkles className="w-3 h-3 text-white" />
                  </div>
                  <span className="font-semibold text-sm">AARA OS</span>
                </div>
                <p className="text-xs text-foreground/50">AI Research Operating System</p>
              </div>
              {[
                ['Product', ['Features', 'Pricing', 'API']],
                ['Company', ['About', 'Blog', 'Contact']],
                ['Legal', ['Privacy', 'Terms']],
              ].map(([title, links]) => (
                <div key={title as string}>
                  <h4 className="font-medium text-xs text-foreground/70 mb-3 uppercase tracking-wider">{title as string}</h4>
                  <ul className="space-y-2">
                    {(links as string[]).map((link) => (
                      <li key={link}><Link href="#" className="text-xs text-foreground/50 hover:text-foreground transition-colors">{link}</Link></li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            <div className="border-t border-border/30 pt-6 text-center text-xs text-foreground/40">&copy; 2024 AARA OS. All rights reserved.</div>
          </div>
        </footer>
      </main>
    </>
  )
}
