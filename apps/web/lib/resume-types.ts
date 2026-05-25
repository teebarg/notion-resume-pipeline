export interface Basics {
  name: string;
  title: string;
  summary: string;
  email: string;
  location: string;
  website: string;
  linkedin: string;
  github: string;
}

export interface Experience {
  company: string;
  role: string;
  location: string;
  startDate: string;
  endDate: string;
  current: boolean;
  highlights: string[];
}


export interface Project {
  name: string;
  description: string;
  tech: string[];
  link?: string | null;
}

export interface Education {
  degree: string;
  field: string;
  institution: string;
  startDate: string;
  endDate: string;
}

export interface Skill {
  name: string;
  stack: string[];
}


export interface ResumeData {
  basics: Basics;
  experience: Experience[];
  education: Education[];
  skills: Skill[];
  projects: Project[];
}


export type TemplateId = "minimal" | "modern" | "classic" | "developer";

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
  basics: {
    name: '',
    title: '',
    email: '',
    // phone: '',
    location: '',
    website: '',
    linkedin: '',
    github: '',
    summary: '',
  },
  experience: [],
  education: [],
  skills: [],
  projects: [],
}
