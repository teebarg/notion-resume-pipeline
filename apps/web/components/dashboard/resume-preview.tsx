"use client";

import { cn } from "@/lib/utils";
import type { ResumeData, TemplateId } from "@/lib/resume-types";
import { Mail, Phone, MapPin, Globe, Linkedin, Github, Calendar, ExternalLink } from "lucide-react";

interface ResumePreviewProps {
    data: ResumeData;
    template: TemplateId;
}

const formatDate = (date: string) => {
    return date;
    if (!date) return "";
    const [year, month] = date.split("-");
    console.log([year, month]);
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return `${months[parseInt(month) - 1]} ${year}`;
};

export function ResumePreview({ data, template }: ResumePreviewProps) {
    const basic = data.basics;
    const isEmpty = !basic.name && !basic.title && data.experience.length === 0;

    if (isEmpty) {
        return (
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
        );
    }

    const templateStyles = {
        minimal: {
            container: "font-sans",
            header: "text-center border-b pb-4 mb-6",
            name: "text-2xl font-bold tracking-tight",
            title: "text-sm text-muted-foreground mt-1",
            section: "mb-5",
            sectionTitle: "text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 border-b pb-1",
            accent: "text-foreground",
        },
        modern: {
            container: "font-sans",
            header: "mb-6",
            name: "text-2xl font-bold text-blue-600 dark:text-blue-400",
            title: "text-sm text-muted-foreground mt-1",
            section: "mb-5",
            sectionTitle: "text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400 mb-3",
            accent: "text-blue-600 dark:text-blue-400",
        },
        classic: {
            container: "font-serif",
            header: "text-center border-b-2 border-amber-600/30 pb-4 mb-6",
            name: "text-2xl font-bold",
            title: "text-sm text-muted-foreground mt-1 italic",
            section: "mb-5",
            sectionTitle: "text-sm font-bold uppercase tracking-wide mb-3 border-b border-amber-600/30 pb-1",
            accent: "text-amber-700 dark:text-amber-500",
        },
        developer: {
            container: "font-mono",
            header: "mb-6 border-l-4 border-emerald-500 pl-4",
            name: "text-2xl font-bold",
            title: "text-sm text-emerald-600 dark:text-emerald-400 mt-1",
            section: "mb-5",
            sectionTitle:
                'text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-3 flex items-center gap-2 before:content-["//"]',
            accent: "text-emerald-600 dark:text-emerald-400",
        },
    };

    const styles = templateStyles[template];

    return (
        <div className={cn("h-full overflow-auto p-8 text-sm", styles.container)}>
            {/* Header */}
            <header className={styles.header}>
                <h1 className={styles.name}>{basic.name}</h1>
                <p className={styles.title}>{basic.title}</p>

                <div className="mt-3 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                    {data.basics.email && (
                        <span className="flex items-center gap-1">
                            <Mail className="h-3 w-3" />
                            {data.basics.email}
                        </span>
                    )}
                    {/* {data.phone && (
            <span className="flex items-center gap-1">
              <Phone className="h-3 w-3" />
              {data.phone}
            </span>
          )} */}
                    {basic.location && (
                        <span className="flex items-center gap-1">
                            <MapPin className="h-3 w-3" />
                            {basic.location}
                        </span>
                    )}
                    {basic.website && (
                        <span className="flex items-center gap-1">
                            <Globe className="h-3 w-3" />
                            {basic.website}
                        </span>
                    )}
                    {basic.linkedin && (
                        <span className="flex items-center gap-1">
                            <Linkedin className="h-3 w-3" />
                            {basic.linkedin}
                        </span>
                    )}
                    {basic.github && (
                        <span className="flex items-center gap-1">
                            <Github className="h-3 w-3" />
                            {basic.github}
                        </span>
                    )}
                </div>
            </header>

            {/* Summary */}
            {basic.summary && (
                <section className={styles.section}>
                    <h2 className={styles.sectionTitle}>Summary</h2>
                    <p className="text-muted-foreground leading-relaxed">{basic.summary}</p>
                </section>
            )}

            {/* Experience */}
            {data.experience.length > 0 && (
                <section className={styles.section}>
                    <h2 className={styles.sectionTitle}>Experience</h2>
                    <div className="space-y-4">
                        {data.experience?.map((exp, i: number) => (
                            <div key={i}>
                                <div className="flex items-start justify-between gap-2">
                                    <div>
                                        <h3 className="font-semibold">{exp.role}</h3>
                                        <p className={cn("text-sm", styles.accent)}>{exp.company}</p>
                                    </div>
                                    <div className="flex shrink-0 items-center gap-1 text-xs text-muted-foreground">
                                        <Calendar className="h-3 w-3" />
                                        {formatDate(exp.startDate)} - {exp.current ? "Present" : formatDate(exp.endDate)}
                                    </div>
                                </div>
                                {exp.location && <p className="text-xs text-muted-foreground">{exp.location}</p>}
                                <ul className="mt-2 space-y-1">
                                    {exp.highlights?.map((item, i: number) => (
                                        <li key={i} className="flex gap-2 text-muted-foreground">
                                            <span className={styles.accent}>•</span>
                                            {item}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        ))}
                    </div>
                </section>
            )}

            {/* Skills */}
            {data.skills.length > 0 && (
                <section className={styles.section}>
                    <h2 className={styles.sectionTitle}>Skills</h2>
                    <div className="flex flex-wrap gap-1.5">
                        {data.skills?.map((skill, i) => (
                            <span
                                key={i}
                                className={cn(
                                    "rounded-md px-2 py-0.5 text-xs",
                                    template === "minimal" && "bg-muted",
                                    template === "modern" && "bg-blue-500/10 text-blue-700 dark:text-blue-300",
                                    template === "classic" && "border border-amber-600/30",
                                    template === "developer" && "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-mono"
                                )}
                            >
                                {skill.name}
                            </span>
                        ))}
                    </div>
                </section>
            )}

            {/* Projects */}
            {data.projects.length > 0 && (
                <section className={styles.section}>
                    <h2 className={styles.sectionTitle}>Projects</h2>
                    <div className="space-y-3">
                        {data.projects?.map((project, i: number) => (
                            <div key={i}>
                                <div className="flex items-center gap-2">
                                    <h3 className="font-semibold">{project.name}</h3>
                                    {project.link && <ExternalLink className={cn("h-3 w-3", styles.accent)} />}
                                </div>
                                <p className="text-muted-foreground">{project.description}</p>
                                <div className="mt-1 flex flex-wrap gap-1">
                                    {project.tech?.map((tech, i) => (
                                        <span key={i} className="text-xs text-muted-foreground">
                                            {tech}
                                            {i < project.tech.length - 1 && " •"}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </section>
            )}

            {/* Education */}
            {data.education.length > 0 && (
                <section className={styles.section}>
                    <h2 className={styles.sectionTitle}>Education</h2>
                    <div className="space-y-3">
                        {data.education?.map((edu, i: number) => (
                            <div key={i}>
                                <div className="flex items-start justify-between gap-2">
                                    <div>
                                        <h3 className="font-semibold">{edu.institution}</h3>
                                        <p className="text-muted-foreground">{edu.degree}</p>
                                    </div>
                                    <div className="flex shrink-0 items-center gap-1 text-xs text-muted-foreground">
                                        <Calendar className="h-3 w-3" />
                                        {formatDate(edu.startDate)} - {formatDate(edu.endDate)}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>
            )}
        </div>
    );
}
