'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { FileText, Download, Eye, Edit2, Check, Plus } from 'lucide-react'
import { GlassCard } from '@/components/ui/glass-card'
import { PageTransition, childVariants } from '@/components/page-transition'
import { SkeletonCard } from '@/components/ui/skeleton'

const templates = [
  { name: 'Academic Report', id: 'academic', description: 'Comprehensive research paper with literature review, gaps, and novel directions', sections: ['Abstract', 'Introduction', 'Literature Review', 'Gap Analysis', 'Novel Directions', 'Conclusion'] },
  { name: 'Executive Summary', id: 'executive', description: 'High-level overview for decision makers and stakeholders', sections: ['Summary', 'Key Findings', 'Recommendations', 'Timeline'] },
  { name: 'Custom Report', id: 'custom', description: 'Build your own report with selected sections and content', sections: ['Abstract', 'Introduction', 'Literature Review', 'Gap Analysis', 'Novel Directions', 'Recommendations', 'Timeline', 'Conclusion'] },
]

export default function ReportGenerationPage() {
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)
  const [selectedSections, setSelectedSections] = useState<string[]>([])
  const [reportName, setReportName] = useState('')
  const [isBuilding, setIsBuilding] = useState(false)

  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplate(templateId)
    const template = templates.find(t => t.id === templateId)
    if (templateId !== 'custom' && template) setSelectedSections(template.sections)
    else setSelectedSections([])
  }

  const toggleSection = (section: string) => {
    setSelectedSections(prev => prev.includes(section) ? prev.filter(s => s !== section) : [...prev, section])
  }

  const handleBuildReport = () => {
    if (selectedTemplate && selectedSections.length > 0 && reportName) {
      setIsBuilding(true)
      setTimeout(() => { setIsBuilding(false); setSelectedTemplate(null); setSelectedSections([]); setReportName('') }, 2000)
    }
  }

  return (
    <PageTransition className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">Report Generation</h1>
        <p className="text-sm text-foreground/50">Generate comprehensive research reports with evidence-backed insights</p>
      </div>

      {selectedTemplate && (
        <GlassCard depth="flat" className="p-5 space-y-5">
          <div className="space-y-4">
            <h3 className="text-sm font-bold">Customize Your Report</h3>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground/70">Report Name</label>
              <input type="text" placeholder="e.g., Deep Learning in Healthcare - Q1 2024"
                value={reportName} onChange={(e) => setReportName(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-muted/50 border border-border/50 text-sm text-foreground placeholder:text-foreground/30 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all" />
            </div>

            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-foreground/70">Sections to Include</h4>
              <div className="grid md:grid-cols-2 gap-2">
                {templates.find(t => t.id === selectedTemplate)?.sections.map((section) => (
                  <div key={section} onClick={() => toggleSection(section)}
                    className={`p-3 rounded-xl border cursor-pointer transition-all flex items-center gap-2 ${selectedSections.includes(section) ? 'bg-primary/10 border-primary' : 'bg-muted/30 border-border/50 hover:border-primary/30'}`}
                  >
                    <div className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 ${selectedSections.includes(section) ? 'bg-primary border-primary' : 'border-foreground/30'}`}>
                      {selectedSections.includes(section) && <Check className="w-2.5 h-2.5 text-primary-foreground" />}
                    </div>
                    <span className="text-xs font-medium">{section}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <button onClick={handleBuildReport} disabled={!reportName || selectedSections.length === 0 || isBuilding}
                className="px-5 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50 shadow-lg shadow-primary/20 transition-all flex items-center gap-2"
              >
                {isBuilding ? <><div className="w-3.5 h-3.5 rounded-full border-2 border-primary-foreground border-t-transparent animate-spin" /> Building...</> : <><Download className="w-3.5 h-3.5" /> Generate Report</>}
              </button>
              <button onClick={() => { setSelectedTemplate(null); setSelectedSections([]); setReportName('') }}
                className="px-5 py-2 rounded-xl bg-muted/50 text-foreground/70 text-xs font-medium hover:bg-muted/30 transition-colors">Cancel</button>
            </div>

            {isBuilding && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-3 rounded-xl bg-primary/10 border border-primary/20 text-primary text-[10px]">
                Your report is being generated with all selected sections...
              </motion.div>
            )}
          </div>
        </GlassCard>
      )}

      <div className="space-y-3">
        <h2 className="text-sm font-semibold">Report Templates</h2>
        <motion.div className="grid md:grid-cols-3 gap-4" initial="hidden" animate="visible" variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.06 } } }}>
          {templates.map((template) => (
            <motion.div key={template.id} variants={childVariants}>
              <div onClick={() => handleTemplateSelect(template.id)}
                className={`p-5 rounded-xl border-2 cursor-pointer transition-all ${
                  selectedTemplate === template.id
                    ? 'bg-primary/10 border-primary shadow-lg shadow-primary/10'
                    : 'bg-background/40 backdrop-blur-xl border-border/40 hover:border-primary/30 hover:shadow-lg'
                }`}
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <FileText className="w-5 h-5 text-primary" />
                    {selectedTemplate === template.id && <Check className="w-4 h-4 text-primary" />}
                  </div>
                  <h3 className="text-sm font-semibold">{template.name}</h3>
                  <p className="text-[10px] text-foreground/50 leading-relaxed">{template.description}</p>
                  <div className="space-y-1">
                    <p className="text-[10px] font-medium text-foreground/40">Includes:</p>
                    <div className="flex flex-wrap gap-1">
                      {template.sections.map((s) => (
                        <span key={s} className="text-[10px] text-foreground/50 bg-muted/30 px-1.5 py-0.5 rounded">{s}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>

      <div className="space-y-3">
        <h2 className="text-sm font-semibold">Generated Reports</h2>
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <motion.div key={i} variants={childVariants}>
              <GlassCard depth="flat" className="p-4">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 space-y-1">
                    <h4 className="text-xs font-semibold">Research Report - Deep Learning in Healthcare</h4>
                    <div className="flex gap-3 text-[10px] text-foreground/40">
                      <span>Generated 2 days ago</span><span>Academic Template</span><span>45 pages</span>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <button className="p-1.5 rounded-lg hover:bg-muted/50 transition-colors"><Eye className="w-3.5 h-3.5 text-foreground/40" /></button>
                    <button className="p-1.5 rounded-lg hover:bg-muted/50 transition-colors"><Edit2 className="w-3.5 h-3.5 text-foreground/40" /></button>
                    <button className="p-1.5 rounded-lg hover:bg-muted/50 transition-colors"><Download className="w-3.5 h-3.5 text-foreground/40" /></button>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </div>
      </div>

      <div className="p-5 rounded-xl bg-primary/5 border border-primary/20 space-y-3">
        <h3 className="text-xs font-semibold">Export Formats</h3>
        <div className="grid md:grid-cols-4 gap-2">
          {['PDF', 'DOCX', 'Markdown', 'LaTeX'].map((format) => (
            <button key={format} className="py-2 rounded-xl bg-primary/10 text-primary text-[10px] font-medium hover:bg-primary/20 transition-colors">
              Export as {format}
            </button>
          ))}
        </div>
      </div>
    </PageTransition>
  )
}
