'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Save, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'
import { GlassCard } from '@/components/ui/glass-card'
import { PageTransition, childVariants } from '@/components/page-transition'
import { apiClient } from '@/lib/api-client'

export default function SettingsPage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [organization, setOrganization] = useState('')
  const [saved, setSaved] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const handleSave = async () => {
    setIsSaving(true)
    setSaveError(null)
    try {
      await apiClient.updateProfile({ name, email })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch {
      setSaveError('Failed to save settings. Backend may be unavailable.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <PageTransition className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-sm text-foreground/50">Manage your account and application preferences</p>
      </div>

      {saved && (
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="p-3 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400 flex items-center gap-2 text-xs">
          <CheckCircle className="w-4 h-4" />
          Settings saved successfully
        </motion.div>
      )}

      {saveError && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-400">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {saveError}
        </div>
      )}

      <div className="space-y-6">
        <div className="space-y-3">
          <h2 className="text-sm font-semibold">Account Settings</h2>
          <GlassCard depth="flat" className="p-5 space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground/70">Full Name</label>
              <input type="text" placeholder="John Doe" value={name} onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-muted/50 border border-border/50 text-sm text-foreground placeholder:text-foreground/30 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all" />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground/70">Email</label>
              <input type="email" placeholder="john@example.com" value={email} onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-muted/50 border border-border/50 text-sm text-foreground placeholder:text-foreground/30 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all" />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground/70">Organization</label>
              <input type="text" placeholder="Your Organization" value={organization} onChange={(e) => setOrganization(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-muted/50 border border-border/50 text-sm text-foreground placeholder:text-foreground/30 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all" />
            </div>
            <button onClick={handleSave} disabled={isSaving}
              className="flex items-center gap-2 px-5 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors shadow-lg shadow-primary/20 disabled:opacity-50"
            >
              {isSaving ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving...</> : <><Save className="w-4 h-4" /> Save Changes</>}
            </button>
          </GlassCard>
        </div>

        <div className="space-y-3">
          <h2 className="text-sm font-semibold">Privacy & Security</h2>
          <GlassCard depth="flat" className="p-5 space-y-3">
            {[
              { label: 'Share research insights with community', enabled: false },
              { label: 'Allow research data for training', enabled: false },
              { label: 'Two-factor authentication', enabled: true },
              { label: 'Enable session timeout (30 min)', enabled: true },
            ].map((setting, i) => (
              <div key={i} className="flex items-center justify-between p-3 rounded-lg hover:bg-muted/20 transition-colors">
                <label className="text-xs text-foreground/70 cursor-pointer">{setting.label}</label>
                <input type="checkbox" defaultChecked={setting.enabled}
                  className="w-4 h-4 rounded border-border/50 accent-primary cursor-pointer" />
              </div>
            ))}
          </GlassCard>
        </div>

        <div className="space-y-3">
          <h2 className="text-sm font-semibold">API Configuration</h2>
          <GlassCard depth="flat" className="p-5 space-y-4">
            <div className="p-3 rounded-xl bg-primary/5 border border-primary/20 flex gap-2">
              <AlertCircle className="w-4 h-4 text-primary shrink-0 mt-0.5" />
              <p className="text-[10px] text-foreground/60">Configure API endpoints for backend integration.</p>
            </div>
            {[
              { label: 'API Base URL', placeholder: 'https://api.example.com', type: 'url' },
              { label: 'API Key', placeholder: 'Enter your API key', type: 'password' },
            ].map((field) => (
              <div key={field.label} className="space-y-1.5">
                <label className="text-xs font-medium text-foreground/70">{field.label}</label>
                <input type={field.type} placeholder={field.placeholder}
                  className="w-full px-3 py-2 rounded-xl bg-muted/50 border border-border/50 text-sm text-foreground placeholder:text-foreground/30 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all font-mono" />
              </div>
            ))}
            <button className="px-5 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors shadow-lg shadow-primary/20">
              Test Connection
            </button>
          </GlassCard>
        </div>

        <div className="space-y-3">
          <h2 className="text-sm font-semibold">Preferences</h2>
          <GlassCard depth="flat" className="p-5 space-y-4">
            {[
              { label: 'Theme', options: ['Dark Mode', 'Light Mode', 'Auto'] },
              { label: 'Default Citation Format', options: ['APA', 'MLA', 'Chicago', 'BibTeX'] },
              { label: 'Notifications', options: ['All', 'Important only', 'None'] },
            ].map((pref) => (
              <div key={pref.label} className="space-y-1.5">
                <label className="text-xs font-medium text-foreground/70">{pref.label}</label>
                <select className="w-full px-3 py-2 rounded-xl bg-muted/50 border border-border/50 text-sm text-foreground focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all">
                  {pref.options.map((opt) => <option key={opt}>{opt}</option>)}
                </select>
              </div>
            ))}
          </GlassCard>
        </div>

        <div className="space-y-3">
          <h2 className="text-sm font-semibold">Danger Zone</h2>
          <div className="p-5 rounded-xl bg-red-500/5 border border-red-500/20 space-y-3">
            <p className="text-[10px] text-foreground/60">These actions are irreversible and will permanently delete your data.</p>
            <div className="flex gap-2">
              <button className="px-5 py-2 rounded-xl border border-red-500/30 text-red-400 text-xs font-medium hover:bg-red-500/10 transition-colors">Delete Account</button>
              <button className="px-5 py-2 rounded-xl border border-red-500/30 text-red-400 text-xs font-medium hover:bg-red-500/10 transition-colors">Delete All Data</button>
            </div>
          </div>
        </div>
      </div>
    </PageTransition>
  )
}
