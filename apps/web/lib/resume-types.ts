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

export interface ResumeResponse {
  page_id: string;
  resume: ResumeData;
  message: string;
}

export type TemplateId = "minimal" | "modern" | "classic" | "developer" | "modern-sidebar";

export interface Template {
  id: TemplateId
  name: string
  description: string
  preview: string
}
