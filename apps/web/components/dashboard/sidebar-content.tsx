import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sparkles, Settings2, Wand2, Check } from "lucide-react";
import { ResumeData, TemplateId } from "@/lib/resume-types";
import { TemplateSelector } from "./template-selector";

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
    onLoadDemo: () => void;
}

export function SidebarContent({ resume, templateId, variantId, onSelect, onImportClick, onLoadDemo }: SidebarContentProps) {
    return (
        <div className="space-y-6">
            <div>
                <Button variant="outline" className="w-full justify-start gap-2 h-auto py-3" onClick={onImportClick}>
                    <NotionGlyph />
                    <div className="text-left">
                        <div className="text-sm font-medium">Import from Notion</div>
                        <div className="text-xs text-muted-foreground">Sync from a Notion page</div>
                    </div>
                </Button>
                <Button
                    variant="outline"
                    size="sm"
                    className="w-full justify-start gap-2 mt-2 border-dashed text-muted-foreground hover:text-foreground"
                    onClick={onLoadDemo}
                >
                    <Wand2 className="w-3.5 h-3.5" />
                    Try Demo Resume
                </Button>
                {resume ? (
                    <div className="mt-3 rounded-md border border-border bg-card/60 px-3 py-2">
                        <div className="flex items-center gap-2">
                            <span className="relative flex w-2 h-2">
                                <span className="absolute inset-0 rounded-full bg-emerald-500/60 animate-ping" />
                                <span className="relative inline-block w-2 h-2 rounded-full bg-emerald-500" />
                            </span>
                            <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                                Loaded
                            </span>
                        </div>
                        <div className="mt-1 text-sm font-medium truncate">{resume.basics.name}</div>
                    </div>
                ) : (
                    <div className="mt-3 rounded-md border border-dashed border-border bg-card/30 px-3 py-2">
                        <div className="flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-muted-foreground/40" />
                            <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                                Idle
                            </span>
                        </div>
                        <div className="mt-1 text-xs text-muted-foreground">No resume loaded yet</div>
                    </div>
                )}
            </div>

            <div>
                <p className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-3">Templates</p>
                <TemplateSelector onSelect={onSelect} selectedTemplateId={templateId} selectedVariantId={variantId} />
            </div>

            <div>
                <p className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-3">Actions</p>
                <div className="space-y-1.5">
                    <Button variant="ghost" size="sm" className="w-full justify-start gap-2 text-muted-foreground">
                        <Sparkles className="w-4 h-4" /> Tailor with AI
                    </Button>
                    <Button variant="ghost" size="sm" className="w-full justify-start gap-2 text-muted-foreground">
                        <Settings2 className="w-4 h-4" /> Edit content
                    </Button>
                </div>
                <div className="mt-3 rounded-md border border-border bg-card/40 px-3 py-2.5">
                    <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-2">
                        Outputs
                    </div>
                    <ul className="grid grid-cols-2 gap-y-1 text-xs text-muted-foreground">
                        {["PDF", "Markdown", "JSON", "Live Preview"].map((o) => (
                            <li key={o} className="flex items-center gap-1.5">
                                <Check className="w-3 h-3 text-emerald-500" />
                                <span>{o}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            </div>
        </div>
    );
}
