'use client'

import { AnimatedSidebar } from '@/components/animated-sidebar'
import { Header } from '@/components/header'
import { motion } from 'framer-motion'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Header />
      <div className="flex h-[calc(100vh-56px)]">
        <AnimatedSidebar />
        <motion.main
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="flex-1 overflow-y-auto scrollbar-thin"
        >
          <div className="p-6 lg:p-8 max-w-7xl mx-auto">{children}</div>
        </motion.main>
      </div>
    </>
  )
}
