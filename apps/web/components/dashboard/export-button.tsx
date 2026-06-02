"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Spinner } from "@/components/ui/spinner";
import { Download, FileText, ChevronDown, FileDown } from "lucide-react";
import type { ResumeData, TemplateId } from "@/lib/resume-types";
import { toast } from "sonner";
import { downloadMarkdown } from "@/lib/resume-markdown";

interface ExportButtonProps {
    pageId: string | null;
    data: ResumeData;
    template: TemplateId;
    disabled?: boolean;
}

export function ExportButton({ pageId, data, template, disabled }: ExportButtonProps) {
    const toastId = useRef<string | number | undefined>(undefined);
    const [isExporting, setIsExporting] = useState(false);

    if (!pageId) {
        return;
    }

    const handleExportPDF = async () => {
        setIsExporting(true);
        toastId.current = toast.loading("Generating PDF...");
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/notion/pdf/${pageId}?template=${template}`);

            if (!res.ok) throw new Error("Failed to download PDF");

            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            toast.success("Done! PDF Downloaded", { id: toastId.current });

            const a = document.createElement("a");
            a.href = url;
            a.download = `${data.basics.name.replace(/\s+/g, "_")}_Resume.pdf`;
            document.body.appendChild(a);
            a.click();

            a.remove();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error("Export error:", error);
            toast.error("Failed! Try again later", { id: toastId.current });
        } finally {
            setIsExporting(false);
        }
    };

    const handleExportJSON = () => {
        const jsonString = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonString], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${data.basics.name.replace(/\s+/g, "_")}_Resume.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const handleExportMarkdown = () => {
        downloadMarkdown(data);
        toast("Markdown exported", { description: `${data.basics.name}.md downloaded.` });
    };

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button size="sm" disabled={disabled || isExporting} className="gap-2">
                    {isExporting ? <Spinner className="h-4 w-4" /> : <Download className="h-4 w-4" />}
                    <span className="hidden xs:inline sm:inline">Export</span>
                    <ChevronDown className="hidden xs:inline sm:inline h-3 w-3" />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={handleExportPDF}>
                    <FileText className="mr-2 h-4 w-4" />
                    Export as PDF
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleExportJSON}>
                    <Download className="mr-2 h-4 w-4" />
                    Export as JSON
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleExportMarkdown}>
                    <FileDown className="mr-2 h-4 w-4" />
                    Export as Markdown
                </DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
    );
}
