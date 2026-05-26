'use client'

import { useState } from 'react'
import { Header } from '@/components/dashboard/header'
import { NotionImport } from '@/components/dashboard/notion-import'
import { TemplateSelector } from '@/components/dashboard/template-selector'
import { ResumePreview } from '@/components/dashboard/resume-preview'
import { ExportButton } from '@/components/dashboard/export-button'
import { Card, CardContent } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { defaultResumeData, type ResumeData, type TemplateId } from '@/lib/resume-types'

export default function DashboardPage() {
  const [resumeData, setResumeData] = useState<ResumeData>(defaultResumeData)
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateId>('minimal')

  const hasData = resumeData.basics.name || resumeData.experience.length > 0

  return (
      <div className="flex min-h-screen flex-col">
          <Header />

          <main className="flex flex-1 flex-col lg:flex-row">
              {/* Sidebar */}
              <aside className="w-full shrink-0 border-b border-border/40 bg-muted/20 lg:w-80 lg:border-b-0 lg:border-r">
                  <div className="flex h-full flex-col p-6">
                      <div className="space-y-1">
                          <h2 className="text-lg font-semibold tracking-tight">Resume Builder</h2>
                          <p className="text-sm text-muted-foreground">Import your resume and customize the template</p>
                      </div>

                      <Separator className="my-6" />

                      {/* Import Section */}
                      <div className="space-y-4">
                          <NotionImport onImport={setResumeData} />
                      </div>

                      <Separator className="my-6" />

                      {/* Template Selection */}
                      <TemplateSelector selected={selectedTemplate} onSelect={setSelectedTemplate} />

                      <div className="mt-6 lg:mt-auto lg:pt-6">
                          <ExportButton data={resumeData} template={selectedTemplate} disabled={!hasData} />
                      </div>
                  </div>
              </aside>

              {/* Preview Area */}
              <div className="flex flex-1 flex-col bg-muted/30">
                  <div className="flex items-center justify-between border-b border-border/40 px-6 py-3">
                      <div className="flex items-center gap-2">
                          <div className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                          <span className="text-sm text-muted-foreground">Live Preview</span>
                      </div>
                      {hasData && (
                          <span className="hidden text-xs text-muted-foreground sm:block">
                              {resumeData.basics.name} • {selectedTemplate.charAt(0).toUpperCase() + selectedTemplate.slice(1)} Template
                          </span>
                      )}
                  </div>

                  <div className="flex flex-1 items-center justify-center p-4 sm:p-8">
                      <Card className="aspect-[8.5/11] w-full max-w-2xl overflow-hidden shadow-2xl">
                          <CardContent className="h-full p-0">
                              <iframe
                                  src="http://127.0.0.1:8000/api/v1/notion/preview/2e38c0a7df7180f6947ffe355c4d8e9b?template=minimal"
                                  className="w-full h-screen"
                              />
                              <ResumePreview data={resumeData} template={selectedTemplate} />
                          </CardContent>
                      </Card>
                  </div>
              </div>
          </main>
      </div>
  );
}
