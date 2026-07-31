import { Wand2, FileQuestion } from "lucide-react";

const NotionGlyph = () => (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="currentColor">
        <path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.981-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.841-.046.935-.56.935-1.167V6.354c0-.606-.233-.933-.748-.887l-15.177.887c-.56.047-.747.327-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952l1.448.327s0 .84-1.168.84l-3.222.187c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.139c-.093-.514.28-.887.747-.933z" />
    </svg>
);

interface EmptyPreviewProps {
    onImportClick: () => void;
    onLoadDemo: () => void;
}


export function EmptyPreview({ onImportClick, onLoadDemo }: EmptyPreviewProps) {
    return (
        <div className="w-[210mm] h-[197mm] flex items-center justify-center bg-zinc-50">
            <div className="max-w-[60%] text-center space-y-5">
                <div className="mx-auto w-20 h-20 rounded-xl border border-dashed border-zinc-500 bg-white flex items-center justify-center">
                    <FileQuestion className="w-12 h-12 text-zinc-500" />
                </div>
                <div className="space-y-1.5">
                    <div className="font-mono uppercase tracking-widest text-zinc-400">
                        empty state
                    </div>
                    <h3 className="text-zinc-900 text-2xl font-semibold tracking-tight">
                        No resume to preview
                    </h3>
                    <p className="text-zinc-500 leading-relaxed">
                        Import a Notion page or load the demo resume to see the live, print-ready preview render here.
                    </p>
                </div>
                <div className="flex items-center justify-center gap-2 pt-1">
                    <button
                        onClick={onImportClick}
                        className="inline-flex items-center gap-1.5 h-12 px-3 rounded-md bg-zinc-900 text-white font-medium hover:bg-zinc-800 transition-colors"
                    >
                        <NotionGlyph />
                        Import from Notion
                    </button>
                    <button
                        onClick={onLoadDemo}
                        className="inline-flex items-center gap-1.5 h-12 px-3 rounded-md border border-dashed border-zinc-300 text-zinc-600 font-medium hover:border-zinc-400 hover:text-zinc-900 transition-colors"
                    >
                        <Wand2 className="w-3.5 h-3.5" />
                        Try demo
                    </button>
                </div>
                <div className="pt-2 text-sm font-mono text-zinc-500">
                    waiting for input · /api/render-resume idle
                </div>
            </div>
        </div>
    );
}
