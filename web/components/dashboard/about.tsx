import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
    DialogTrigger,
} from "@/components/ui/dialog";
import {
    FileText, Github, Info
} from "lucide-react";

export function About() {
    return (
        <Dialog>
            <DialogTrigger asChild>
                <Button variant="ghost" size="icon" aria-label="About" title="About">
                    <Info className="w-4 h-4" />
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md p-0 overflow-hidden border-border bg-card">
                <div className="p-5 border-b border-border flex items-center gap-3">
                    <div className="w-9 h-9 rounded-md bg-primary/15 border border-primary/30 flex items-center justify-center">
                        <FileText className="w-4.5 h-4.5 text-primary" />
                    </div>
                    <div className="min-w-0">
                        <DialogHeader className="p-0 space-y-0.5">
                            <DialogTitle className="text-base font-semibold tracking-tight">RenderCV</DialogTitle>
                            <DialogDescription className="text-xs text-muted-foreground">
                                Developer-first resume rendering engine.
                            </DialogDescription>
                        </DialogHeader>
                    </div>
                    <Badge variant="secondary" className="ml-auto font-mono text-[10px] py-0">v1.4.0</Badge>
                </div>
                <div className="p-5 space-y-3">
                    <div className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
                        Pipeline
                    </div>
                    <pre className="text-[12px] font-mono leading-6 text-foreground/85 whitespace-pre rounded-md border border-border bg-muted/30 px-4 py-3">
                        {`Notion API
      ↓
Normalization
      ↓
ResumeData Schema
      ↓
HTML Template Engine
      ↓
Preview / PDF / Markdown / JSON`}
                    </pre>
                    <div className="flex items-center justify-between pt-1">
                        <span className="text-[11px] font-mono text-muted-foreground">
                            built for portfolios · open source
                        </span>
                        <a
                            href="https://github.com/teebarg"
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1.5 text-[11px] font-mono text-muted-foreground hover:text-foreground transition-colors"
                        >
                            <Github className="w-3.5 h-3.5" /> source
                        </a>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}
