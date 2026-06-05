import { ResumeData } from "./resume-types";


export function resumeToMarkdown(d: ResumeData): string {
    const lines: string[] = [];
    lines.push(`# ${d.basics.name}`);
    lines.push(`*${d.basics.title}*`);
    lines.push("");
    lines.push(
        [d.basics.location, d.basics.email, d.basics.website, d.basics.github].filter(Boolean).join(" · "),
    );
    lines.push("");

    if (d.basics.summary) {
        lines.push("## Summary", "", d.basics.summary, "");
    }

    if (d.experience.length) {
        lines.push("## Experience", "");
        for (const e of d.experience) {
            lines.push(`### ${e.role} — ${e.company}`);
            lines.push(`*${e.startDate} - ${e.endDate}${e.location ? ` · ${e.location}` : ""}*`, "");
            for (const b of e.highlights) lines.push(`- ${b}`);
            lines.push("");
        }
    }

    if (d.projects.length) {
        lines.push("## Projects", "");
        for (const p of d.projects) {
            const head = p.link ? `### [${p.name}](${p.link})` : `### ${p.name}`;
            lines.push(head);
            lines.push(p.description);
            if (p.stack.length) lines.push("", `\`${p.stack.join("` · `")}\``);
            lines.push("");
        }
    }

    if (d.skills.length) {
        lines.push("## Skills", "");
        for (const s of d.skills) lines.push(`- **${s.name}:** ${s.stack.join(", ")}`);
        lines.push("");
    }

    if (d.education.length) {
        lines.push("## Education", "");
        for (const ed of d.education) {
            lines.push(`- **${ed.institution}** — ${ed.degree} *(${ed.startDate} - ${ed.endDate})*`);
        }
        lines.push("");
    }

    return lines.join("\n").trimEnd() + "\n";
}

export function downloadMarkdown(d: ResumeData) {
    const md = resumeToMarkdown(d);
    const slug = d.basics.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "resume";
    const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${slug}.md`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
