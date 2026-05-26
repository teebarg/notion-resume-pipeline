'use client'

import { useEffect, useState } from 'react'
import { Header } from '@/components/dashboard/header'
import { NotionImport } from '@/components/dashboard/notion-import'
import { TemplateSelector } from '@/components/dashboard/template-selector'
import { ExportButton } from '@/components/dashboard/export-button'
import { Card, CardContent } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { defaultResumeData, ResumeResponse, type ResumeData, type TemplateId } from '@/lib/resume-types'
import { getPersistedResume } from '@/lib/storage'

export default function DashboardPage() {
    const [loading, setLoading] = useState<boolean>(true);
    const [pageId, setPageId] = useState<string | null>(getPersistedResume())
    const [resumeData, setResumeData] = useState<ResumeData>(defaultResumeData)
    const [selectedTemplate, setSelectedTemplate] = useState<TemplateId>('minimal')

    const onImport = (data: ResumeResponse) => {
        setResumeData(data.resume)
        setPageId(data.page_id)
    }

    useEffect(() => {
        if (pageId) setLoading(true);
    }, [pageId, selectedTemplate]);

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
                            <NotionImport onImport={onImport} />
                        </div>

                        <Separator className="my-6" />

                        {/* Template Selection */}
                        <TemplateSelector selected={selectedTemplate} onSelect={setSelectedTemplate} />

                        <div className="mt-6 lg:mt-auto lg:pt-6">
                            <ExportButton pageId={pageId} data={resumeData} template={selectedTemplate} disabled={!Boolean(pageId)} />
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
                    </div>

                    <div className="flex flex-1 items-center justify-center p-4 sm:p-8">
                        <Card className="aspect-[8.5/11] w-full max-w-2xl overflow-hidden shadow-2xl">
                            <CardContent className="h-full p-0">
                                {pageId ? (
                                    <>
                                        {loading && (
                                            <div className="absolute inset-0 p-6 space-y-3 animate-pulse bg-white">
                                                <div className="h-6 w-1/2 bg-gray-200 rounded" />
                                                <div className="h-4 w-full bg-gray-100" />
                                                <div className="h-4 w-5/6 bg-gray-100" />
                                                <div className="h-4 w-2/3 bg-gray-100" />
                                            </div>
                                        )}

                                        <iframe
                                            src={`${process.env.NEXT_PUBLIC_API_URL}/api/v1/notion/preview/${pageId}?template=${selectedTemplate}`}
                                            className="h-full w-full"
                                            onLoad={() => setLoading(false)}
                                        />
                                    </>
                                ) : (
                                    <div className="flex h-full flex-col items-center justify-center text-center">
                                        <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
                                            <svg className="h-8 w-8 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                    strokeWidth={1.5}
                                                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                                                />
                                            </svg>
                                        </div>
                                        <h3 className="text-lg font-medium">No resume data yet</h3>
                                        <p className="mt-1 text-sm text-muted-foreground">Import from Notion or load sample data to preview</p>
                                    </div>
                                )}
                                {/* <ResumePreview data={resumeData} template={selectedTemplate} /> */}
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </main>
        </div>
    );
}
