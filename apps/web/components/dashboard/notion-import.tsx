'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Spinner } from '@/components/ui/spinner'
import { Import, ExternalLink, CheckCircle2, AlertCircle } from 'lucide-react'
import type { ResumeData, Experience, Education, Project } from '@/lib/resume-types'

interface NotionImportProps {
  onImport: (data: ResumeData) => void
}

type ImportStatus = 'idle' | 'loading' | 'success' | 'error'

export function NotionImport({ onImport }: NotionImportProps) {
  const [open, setOpen] = useState(false)
  const [pageUrl, setPageUrl] = useState('')
  const [status, setStatus] = useState<ImportStatus>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  const extractPageId = (url: string): string | null => {
    // Handle various Notion URL formats
    const patterns = [
      /([a-f0-9]{32})/i,
      /([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/i,
    ]

    for (const pattern of patterns) {
      const match = url.match(pattern)
      if (match) return match[1].replace(/-/g, '')
    }
    return null
  }

  const handleImport = async () => {
    const pageId = extractPageId(pageUrl)
    if (!pageId) {
      setStatus('error')
      setErrorMessage('Invalid Notion page URL. Please check and try again.')
      return
    }

    setStatus('loading')
    setErrorMessage('')

    try {
      const response = await fetch('/api/notion/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pageId }),
      })

      if (!response.ok) {
        throw new Error('Failed to import from Notion')
      }

      const data = await response.json()
      onImport(data.resume)
      setStatus('success')

      setTimeout(() => {
        setOpen(false)
        setStatus('idle')
        setPageUrl('')
      }, 1500)
    } catch {
      setStatus('error')
      setErrorMessage('Failed to import from Notion. Make sure the page is accessible.')
    }
  }

  const loadSampleData = () => {
    const sampleData: ResumeData = {
      name: 'Alex Chen',
      title: 'Senior Full-Stack Developer',
      email: 'alex.chen@email.com',
      phone: '+1 (555) 123-4567',
      location: 'San Francisco, CA',
      website: 'alexchen.dev',
      linkedin: 'linkedin.com/in/alexchen',
      github: 'github.com/alexchen',
      summary: 'Passionate full-stack developer with 6+ years of experience building scalable web applications. Expertise in React, Node.js, and cloud infrastructure. Led teams to deliver products used by millions of users.',
      experience: [
        {
          id: '1',
          company: 'TechCorp Inc.',
          position: 'Senior Full-Stack Developer',
          location: 'San Francisco, CA',
          startDate: '2021-03',
          endDate: '',
          current: true,
          description: [
            'Led development of microservices architecture serving 2M+ daily active users',
            'Reduced API response time by 40% through query optimization and caching strategies',
            'Mentored team of 5 junior developers and established code review practices',
          ],
        },
        {
          id: '2',
          company: 'StartupXYZ',
          position: 'Full-Stack Developer',
          location: 'Remote',
          startDate: '2019-01',
          endDate: '2021-02',
          current: false,
          description: [
            'Built real-time collaboration features using WebSockets and Redis',
            'Implemented CI/CD pipeline reducing deployment time by 60%',
            'Developed mobile-responsive dashboard used by 500+ enterprise clients',
          ],
        },
      ] as Experience[],
      education: [
        {
          id: '1',
          institution: 'University of California, Berkeley',
          degree: 'B.S.',
          field: 'Computer Science',
          startDate: '2014-08',
          endDate: '2018-05',
          gpa: '3.8',
        },
      ] as Education[],
      skills: [
        'TypeScript',
        'React',
        'Node.js',
        'PostgreSQL',
        'AWS',
        'Docker',
        'GraphQL',
        'Redis',
        'Next.js',
        'Tailwind CSS',
      ],
      projects: [
        {
          id: '1',
          name: 'DevFlow',
          description: 'Open-source developer productivity tool with 2k+ GitHub stars',
          technologies: ['Next.js', 'Prisma', 'PostgreSQL'],
          link: 'github.com/alexchen/devflow',
        },
        {
          id: '2',
          name: 'CloudSync',
          description: 'Real-time file synchronization service with E2E encryption',
          technologies: ['Go', 'WebRTC', 'AWS S3'],
          link: 'cloudsync.io',
        },
      ] as Project[],
    }

    onImport(sampleData)
    setStatus('success')

    setTimeout(() => {
      setOpen(false)
      setStatus('idle')
    }, 1000)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="gap-2">
          <Import className="h-4 w-4" />
          Import from Notion
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Import Resume from Notion</DialogTitle>
          <DialogDescription>
            Paste the URL of your Notion resume page. The page should be shared publicly or with your workspace.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="notion-url">Notion Page URL</Label>
            <Input
              id="notion-url"
              placeholder="https://notion.so/your-resume-page..."
              value={pageUrl}
              onChange={(e) => setPageUrl(e.target.value)}
              disabled={status === 'loading'}
            />
          </div>

          {status === 'error' && (
            <div className="flex items-center gap-2 text-sm text-destructive">
              <AlertCircle className="h-4 w-4" />
              {errorMessage}
            </div>
          )}

          {status === 'success' && (
            <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
              <CheckCircle2 className="h-4 w-4" />
              Successfully imported!
            </div>
          )}

          <div className="flex flex-col gap-2">
            <Button
              onClick={handleImport}
              disabled={!pageUrl || status === 'loading'}
              className="w-full"
            >
              {status === 'loading' ? (
                <>
                  <Spinner className="mr-2 h-4 w-4" />
                  Importing...
                </>
              ) : (
                'Import Resume'
              )}
            </Button>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground">Or</span>
              </div>
            </div>

            <Button
              variant="secondary"
              onClick={loadSampleData}
              disabled={status === 'loading'}
              className="w-full"
            >
              Load Sample Resume
            </Button>
          </div>

          <p className="text-xs text-muted-foreground">
            <ExternalLink className="mr-1 inline h-3 w-3" />
            Need help setting up your Notion page? Check our{' '}
            <a href="#" className="underline hover:text-foreground">
              template guide
            </a>
            .
          </p>
        </div>
      </DialogContent>
    </Dialog>
  )
}
