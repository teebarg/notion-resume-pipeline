import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { ResumeResponse } from "@/lib/resume-types";
import { persistResume } from "@/lib/storage";

export function NotionImportDialog({
    open,
    onOpenChange,
    onImport,
}: {
    open: boolean;
    onOpenChange: (o: boolean) => void;
    onImport: (data: ResumeResponse) => void;
}) {
    // const [open, setOpen] = useState(false);
    const [url, setUrl] = useState("");
    const [loading, setLoading] = useState(false);

    const extractPageId = (url: string): string | null => {
        // Handle various Notion URL formats
        const patterns = [/([a-f0-9]{32})/i, /([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/i];

        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match) return match[1].replace(/-/g, "");
        }
        return null;
    };

    const handleImport = async () => {
        if (!url.trim()) {
            toast.error("Paste a Notion page URL");
            return;
        }

        const pageId = extractPageId(url);
        if (!pageId) {
            // setStatus("error");
            toast.error("Invalid Notion page URL. Please check and try again.");
            return;
        }
        setLoading(true);
        // Simulated import — in production wire up via Notion connector.
        // await new Promise((r) => setTimeout(r, 1100));
        try {
            const response = await fetch("/api/notion/import", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ pageId }),
            });

            if (!response.ok) {
                throw new Error("Failed to import from Notion");
            }

            const data = await response.json();
            persistResume(data);
            onImport(data);
            onOpenChange(false);
            // setStatus("success");
            toast.success("Imported from Notion", {
                description: "Your Notion page was parsed and applied.",
            });

            // setTimeout(() => {
            //     setOpen(false);
            //     setStatus("idle");
            //     setPageUrl("");
            // }, 1500);
        } catch {
            // setStatus("error");
            // setErrorMessage("Failed to import from Notion. Make sure the page is accessible.");
            toast.error("An error occurred", {
                description: "Failed to import from Notion. Make sure the page is accessible.",
            });
        } finally {
            setLoading(false);
        }
        // onImport({ ...defaultResume });
        // setLoading(false);
        // onOpenChange(false);
        // toast.success("Imported from Notion", {
        //     description: "Your Notion page was parsed and applied.",
        // });
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Import from Notion</DialogTitle>
                    <DialogDescription>
                        Paste a public Notion page URL containing your resume content. We'll parse the headings, lists, and tables.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-2 py-2">
                    <Label htmlFor="notion-url">Notion page URL</Label>
                    <Input
                        id="notion-url"
                        placeholder="https://www.notion.so/your-resume-..."
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        className="font-mono text-sm"
                    />
                    <p className="text-xs text-muted-foreground">Demo mode: any URL imports sample data. Connect Notion in Settings for live sync.</p>
                </div>
                <DialogFooter>
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>
                        Cancel
                    </Button>
                    <Button onClick={handleImport} disabled={loading}>
                        {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                        Import
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
