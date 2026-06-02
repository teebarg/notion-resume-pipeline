import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetTrigger, SheetTitle, SheetHeader } from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Moon, Sun, FileText, Github, ZoomIn, ZoomOut, Menu, RotateCcw, CloudSync } from "lucide-react";
import { toast } from "sonner";
import { useTheme } from "next-themes";
import { NotionImportDialog } from "./dashboard/notion-import-dialog";
import { getPersistedResume, persistResume } from "@/lib/storage";
import { ResumeData, ResumeResponse, TemplateId } from "@/lib/resume-types";
import { ExportButton } from "./dashboard/export-button";
import { Spinner } from "@/components/ui/spinner";
import { SidebarContent } from "./dashboard/sidebar-content";

export function Dashboard() {
    const toastId = useRef<string | number | undefined>(undefined);
    const { theme, setTheme } = useTheme();
    const [resume, setResume] = useState<ResumeData | undefined>(getPersistedResume()?.resume);
    const [templateId, setTemplateId] = useState<any>("minimal");
    const [variantId, setVariantId] = useState<string>("");
    const [importOpen, setImportOpen] = useState(false);
    const [mobileNavOpen, setMobileNavOpen] = useState(false);
    const [zoom, setZoom] = useState(0.85);
    const [loading, setLoading] = useState<boolean>(true);
    const [pageId, setPageId] = useState<string | null>(getPersistedResume()?.page_id ?? null);
    const [isSyncing, setIsSyncing] = useState(false);

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

    const handleDataSync = async () => {
        setIsSyncing(true);
        toastId.current = toast.loading("Updating from notion...");
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/notion/sync`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ page_id: pageId }),
            });

            if (!res.ok) throw new Error("Failed to update data from notion");
            const data = await res.json();
            persistResume(data);
            setResume(data.resume)
            toast.success("Done! Resume synced from notion", { id: toastId.current });
        } catch (error) {
            console.error("Syncing error:", error);
            toast.error("Failed! Try again later", { id: toastId.current });
        } finally {
            setIsSyncing(false);
        }
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
                            <a href="https://github.com/teebarg" target="_blank" rel="noreferrer">
                                <Github className="w-4 h-4" /> <span className="hidden md:inline">Star</span>
                            </a>
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label="Toggle theme">
                            {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
                        </Button>
                        <div className="w-px h-6 bg-border mx-1 hidden sm:block" />
                        {resume && (
                            <Button onClick={handleDataSync} size="sm" disabled={isSyncing} className="gap-2">
                                {isSyncing ? <Spinner className="h-4 w-4" /> : <CloudSync className="h-4 w-4" />}
                                <span className="hidden xs:inline sm:inline">Update</span>
                            </Button>
                        )}
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
                            <p>preview</p>
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
