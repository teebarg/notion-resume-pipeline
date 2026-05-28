import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ExternalLink, Loader2 } from "lucide-react";
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
            toast.error("Invalid Notion page URL. Please check and try again.");
            return;
        }
        setLoading(true);
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
            toast.success("Imported from Notion", {
                description: "Your Notion page was parsed and applied.",
            });
        } catch {
            toast.error("An error occurred", {
                description: "Failed to import from Notion. Make sure the page is accessible.",
            });
        } finally {
            setLoading(false);
        }
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
                    <p className="text-xs text-muted-foreground">
                        <ExternalLink className="mr-1 inline h-3 w-3" />
                        Need help setting up your Notion page? Check our{" "}
                        <a href="#" className="underline hover:text-foreground">
                            template guide
                        </a>
                        .
                    </p>
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
