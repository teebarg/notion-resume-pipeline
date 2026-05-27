import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetTrigger, SheetTitle, SheetHeader } from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileDown, Moon, Sun, Sparkles, FileText, Settings2, Github, ZoomIn, ZoomOut, Menu, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { useTheme } from "next-themes";
import { TemplateSelector } from "./dashboard/template-selector";
import { NotionImportDialog } from "./dashboard/notion-import-dialog";
import { getPersistedResume } from "@/lib/storage";
import { ResumeData, ResumeResponse, TemplateId } from "@/lib/resume-types";
import { ExportButton } from "./dashboard/export-button";

const NotionGlyph = () => (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="currentColor">
        <path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.981-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.841-.046.935-.56.935-1.167V6.354c0-.606-.233-.933-.748-.887l-15.177.887c-.56.047-.747.327-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952l1.448.327s0 .84-1.168.84l-3.222.187c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.139c-.093-.514.28-.887.747-.933z" />
    </svg>
);

interface SidebarContentProps {
    resume: ResumeData | undefined;
    templateId: TemplateId;
    variantId: string;
    onSelect: (templateId: string, variantId?: string) => void;
    onImportClick: () => void;
}

function SidebarContent({ resume, templateId, variantId, onSelect, onImportClick }: SidebarContentProps) {
    return (
        <div className="space-y-6">
            <div>
                <p className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-3">01 — Source</p>
                <Button variant="outline" className="w-full justify-start gap-2 h-auto py-3" onClick={onImportClick}>
                    <NotionGlyph />
                    <div className="text-left">
                        <div className="text-sm font-medium">Import from Notion</div>
                        <div className="text-xs text-muted-foreground">Sync from a Notion page</div>
                    </div>
                </Button>
                {resume && (
                    <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground px-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                        <span className="font-mono truncate">Loaded: {resume.basics.name}</span>
                    </div>
                )}
            </div>

            <div>
                <p className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-3">02 — Template</p>
                <TemplateSelector onSelect={onSelect} selectedTemplateId={templateId} selectedVariantId={variantId} />
            </div>

            <div>
                <p className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-3">03 — Actions</p>
                <div className="space-y-1.5">
                    <Button variant="ghost" size="sm" className="w-full justify-start gap-2 text-muted-foreground">
                        <Sparkles className="w-4 h-4" /> Tailor with AI
                    </Button>
                    <Button variant="ghost" size="sm" className="w-full justify-start gap-2 text-muted-foreground">
                        <Settings2 className="w-4 h-4" /> Edit content
                    </Button>
                    <Button variant="ghost" size="sm" className="w-full justify-start gap-2 text-muted-foreground">
                        <FileDown className="w-4 h-4" /> Export Markdown
                    </Button>
                </div>
            </div>

            <div className="rounded-lg border border-border bg-card p-3">
                <div className="text-xs font-medium mb-1">Pro tip</div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                    Press <kbd className="px-1.5 py-0.5 bg-muted rounded font-mono text-[10px]">⌘P</kbd> anywhere to open the export dialog.
                </p>
            </div>
        </div>
    );
}

export function Dashboard() {
    const { theme, setTheme } = useTheme();
    const [resume, setResume] = useState<ResumeData | undefined>(getPersistedResume()?.resume);
    const [templateId, setTemplateId] = useState<any>("minimal");
    const [variantId, setVariantId] = useState<string>("");
    const [importOpen, setImportOpen] = useState(false);
    const [mobileNavOpen, setMobileNavOpen] = useState(false);
    const [zoom, setZoom] = useState(0.85);
    const [loading, setLoading] = useState<boolean>(true);
    const [pageId, setPageId] = useState<string | null>(getPersistedResume()?.page_id ?? null);

    const onImport = (data: ResumeResponse) => {
        setResume(data.resume);
        setPageId(data.page_id);
    };

    useEffect(() => {
        if (pageId) setLoading(true);
    }, [pageId, templateId, variantId]);

    // Auto-fit zoom to viewport width on resize (A4 = 210mm ≈ 794px).
    const autoFitZoom = useCallback(() => {
        const w = window.innerWidth;
        if (w < 640) return Math.max(0.35, Math.min(0.55, (w - 32) / 794));
        if (w < 1024) return 0.7;
        return 0.85;
    }, []);

    const fitZoom = useCallback(() => {
        setZoom(autoFitZoom());
    }, [autoFitZoom]);

    // Fit on mount and resize
    useEffect(() => {
        fitZoom();
        window.addEventListener("resize", fitZoom);
        return () => window.removeEventListener("resize", fitZoom);
    }, [fitZoom]);

    // Re-center / auto-fit when template or resume data changes
    useEffect(() => {
        fitZoom();
    }, [templateId, resume, fitZoom]);

    const handleImportClick = () => {
        setMobileNavOpen(false);
        setImportOpen(true);
    };

    const handleSelectedTemplate = (templateId: string, variantId?: string) => {
        setTemplateId(templateId);
        setVariantId(variantId ?? "");
    };

    return (
        <div className="min-h-screen bg-background text-foreground">
            <style>{`
        @media print {
          body * { visibility: hidden !important; }
          #print-root, #print-root * { visibility: visible !important; }
          #print-root { position: absolute; inset: 0; background: white; }
          @page { size: A4; margin: 0; }
        }
      `}</style>

            {/* Top bar */}
            <header className="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur-xl no-print">
                <div className="flex items-center justify-between px-4 sm:px-6 h-14 gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                        <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
                            <SheetTrigger asChild>
                                <Button variant="ghost" size="icon" className="lg:hidden -ml-2" aria-label="Open menu">
                                    <Menu className="w-5 h-5" />
                                </Button>
                            </SheetTrigger>
                            <SheetContent side="left" className="w-[300px] p-5 overflow-y-auto bg-sidebar">
                                <SheetHeader className="mb-4">
                                    <SheetTitle className="text-left">Resume settings</SheetTitle>
                                </SheetHeader>
                                <SidebarContent
                                    resume={resume}
                                    templateId={templateId}
                                    variantId={variantId}
                                    onSelect={(templateId, variantId) => {
                                        handleSelectedTemplate(templateId, variantId);
                                        setMobileNavOpen(false);
                                    }}
                                    onImportClick={handleImportClick}
                                />
                            </SheetContent>
                        </Sheet>
                        <div className="w-7 h-7 rounded-md bg-primary/15 border border-primary/30 flex items-center justify-center shrink-0">
                            <FileText className="w-4 h-4 text-primary" />
                        </div>
                        <span className="font-semibold tracking-tight truncate">résumé.dev</span>
                        <Badge variant="secondary" className="ml-1 font-mono text-[10px] py-0 hidden sm:inline-flex">
                            v1.4.0
                        </Badge>
                    </div>
                    <div className="flex items-center gap-1 sm:gap-2 shrink-0">
                        <Button variant="ghost" size="sm" className="gap-2 text-muted-foreground hidden sm:inline-flex" asChild>
                            <a href="https://github.com" target="_blank" rel="noreferrer">
                                <Github className="w-4 h-4" /> <span className="hidden md:inline">Star</span>
                            </a>
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label="Toggle theme">
                            {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
                        </Button>
                        <div className="w-px h-6 bg-border mx-1 hidden sm:block" />
                        {resume && (
                            <ExportButton pageId={pageId} data={resume} template={templateId} disabled={!Boolean(pageId)} />
                        )}
                    </div>
                </div>
            </header>

            <div className="grid lg:grid-cols-[320px_1fr] h-[calc(100vh-3.6rem)]">
                {/* Desktop sidebar */}
                <aside className="hidden lg:flex flex-col border-r border-border bg-sidebar/40 p-5 no-print sticky top-14 h-[calc(100vh-3.6rem)]">
                    <ScrollArea className="flex-1 -mx-2 px-2">
                        <SidebarContent
                            resume={resume}
                            templateId={templateId}
                            variantId={variantId}
                            onSelect={handleSelectedTemplate}
                            onImportClick={() => setImportOpen(true)}
                        />
                    </ScrollArea>
                </aside>

                {/* Preview */}
                <main className="bg-grid relative overflow-auto">
                    <div className="sticky top-0 z-10 flex items-center justify-between px-4 sm:px-6 py-3 bg-background/80 backdrop-blur-md border-b border-border no-print gap-2">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono min-w-0">
                            <span className="w-2 h-2 rounded-full bg-primary shrink-0" />
                            {/* <span className="truncate">preview · {templates.find((t) => t.id === templateId)?.name.toLowerCase()}.tsx</span> */}
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                            <Button variant="ghost" size="icon" className="w-7 h-7" onClick={() => setZoom((z) => Math.max(0.3, z - 0.1))}>
                                <ZoomOut className="w-3.5 h-3.5" />
                            </Button>
                            <span className="text-xs font-mono w-10 text-center text-muted-foreground">{Math.round(zoom * 100)}%</span>
                            <Button variant="ghost" size="icon" className="w-7 h-7" onClick={() => setZoom((z) => Math.min(1.4, z + 0.1))}>
                                <ZoomIn className="w-3.5 h-3.5" />
                            </Button>
                            <div className="w-px h-4 bg-border mx-1" />
                            <Button variant="ghost" size="icon" className="w-7 h-7" onClick={fitZoom} title="Reset zoom">
                                <RotateCcw className="w-3.5 h-3.5" />
                            </Button>
                        </div>
                    </div>

                    <div className="flex justify-center py-4 px-2 sm:px-4">
                        <div
                            style={{
                                width: `calc(210mm * ${zoom})`,
                                height: `calc(237mm * ${zoom})`,
                            }}
                        >
                            <div
                                style={{
                                    width: "210mm",
                                    transform: `scale(${zoom})`,
                                    transformOrigin: "top left",
                                }}
                                className="transition-transform"
                            >
                                <Card
                                    id="print-root"
                                    className="w-[210mm] min-h-[237mm] bg-white shadow-2xl shadow-black/30 border-0 overflow-hidden p-0 rounded-sm relative"
                                >
                                    {pageId ? (
                                        <iframe
                                            key={pageId}
                                            src={`${process.env.NEXT_PUBLIC_API_URL}/api/v1/notion/preview/${pageId}?template=${templateId}&variant=${variantId}`}
                                            onLoad={() => setLoading(false)}
                                            title="Resume preview"
                                            className="w-[210mm] h-[237mm] block border-0 bg-white"
                                        />
                                    ) : (
                                        <div className="w-[210mm] h-[237mm] flex flex-col items-center justify-center text-zinc-400 text-sm font-mono">
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
                                    {pageId && loading && (
                                        <div className="absolute top-3 right-3 text-[10px] font-mono px-2 py-1 rounded bg-black/70 text-white">
                                            rendering…
                                        </div>
                                    )}
                                </Card>
                            </div>
                        </div>
                    </div>
                </main>
            </div>

            <NotionImportDialog open={importOpen} onOpenChange={setImportOpen} onImport={onImport} />
        </div>
    );
}
