import { Analytics } from '@vercel/analytics/next'
import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { AuthHydrator } from '@/components/auth-hydrator'
import './globals.css'

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] })
const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
})

export const metadata: Metadata = {
  title: 'AARA - AI Research Operating System',
  description: 'Advanced research powered by intelligent agents. Discover papers, analyze gaps, and generate novel research directions.',
  icons: {
    icon: [
      { url: '/icon-light-32x32.png', media: '(prefers-color-scheme: light)' },
      { url: '/icon-dark-32x32.png', media: '(prefers-color-scheme: dark)' },
      { url: '/icon.svg', type: 'image/svg+xml' },
    ],
    apple: '/apple-icon.png',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} dark`}>
      <body className="font-sans antialiased bg-background text-foreground">
        <div className="fixed inset-0 bg-grid pointer-events-none z-0" />
        <div className="fixed top-[-20%] left-[-10%] w-[40%] h-[40%] rounded-full bg-gradient-to-br from-primary/8 to-accent/5 blur-[120px] pointer-events-none z-0" />
        <div className="fixed bottom-[-10%] right-[-10%] w-[50%] h-[30%] rounded-full bg-gradient-to-br from-accent/5 to-primary/8 blur-[100px] pointer-events-none z-0" />
        <div className="relative z-10">
          <AuthHydrator />
          {children}
        </div>
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
