export interface ResumeData {
  name: string
  title: string
  email: string
  phone: string
  location: string
  website: string
  linkedin: string
  github: string
  summary: string
  experience: Experience[]
  education: Education[]
  skills: string[]
  projects: Project[]
}

export interface Experience {
  id: string
  company: string
  position: string
  location: string
  startDate: string
  endDate: string
  current: boolean
  description: string[]
}

export interface Education {
  id: string
  institution: string
  degree: string
  field: string
  startDate: string
  endDate: string
  gpa?: string
}

export interface Project {
  id: string
  name: string
  description: string
  technologies: string[]
  link?: string
}

export type TemplateId = 'minimal' | 'modern' | 'classic' | 'developer'

export interface Template {
  id: TemplateId
  name: string
  description: string
  preview: string
}

export const templates: Template[] = [
  {
    id: 'minimal',
    name: 'Minimal',
    description: 'Clean and simple design with focus on content',
    preview: 'minimal',
  },
  {
    id: 'modern',
    name: 'Modern',
    description: 'Contemporary layout with subtle accents',
    preview: 'modern',
  },
  {
    id: 'classic',
    name: 'Classic',
    description: 'Traditional format preferred by recruiters',
    preview: 'classic',
  },
  {
    id: 'developer',
    name: 'Developer',
    description: 'Technical focus with skills emphasis',
    preview: 'developer',
  },
]

export const defaultResumeData: ResumeData = {
  name: '',
  title: '',
  email: '',
  phone: '',
  location: '',
  website: '',
  linkedin: '',
  github: '',
  summary: '',
  experience: [],
  education: [],
  skills: [],
  projects: [],
}
