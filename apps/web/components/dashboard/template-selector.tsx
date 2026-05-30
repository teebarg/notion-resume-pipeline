"use client";

import { Check } from "lucide-react";
import { useState, useEffect } from "react";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

interface TemplateVariant {
    id: string;
    name: string;
    primary_color: string;
    text_color: string;
}

interface Template {
    id: string;
    name: string;
    description: string;
    preview: string;
    has_sidebar: boolean;
    variants: TemplateVariant[];
}

interface TemplateSelectorProps {
    onSelect: (templateId: string, variantId?: string) => void;
    selectedTemplateId?: string;
    selectedVariantId?: string;
}

export function TemplateSelector({ selectedTemplateId, selectedVariantId, onSelect }: TemplateSelectorProps) {
    const [templates, setTemplates] = useState<Template[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchTemplates = async () => {
            try {
                setLoading(true);
                const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/resumes/templates`);

                if (!response.ok) {
                    throw new Error(`Failed to fetch templates: ${response.statusText}`);
                }

                const data = await response.json();
                setTemplates(data);
            } catch (err) {
                setError(err instanceof Error ? err.message : "An unexpected error occurred");
            } finally {
                setLoading(false);
            }
        };

        fetchTemplates();
    }, []);

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-3 text-gray-600 font-medium text-sm">Loading templates...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
                <p className="font-semibold">Engine Error</p>
                <p>{error}</p>
            </div>
        );
    }

    return (
        <div className="grid grid-cols-2 gap-2 max-h-[60vh] overflow-y-auto thin-scrollbar">
            {templates.map((t: Template) => {
                const active = t.id === selectedTemplateId;
                return (
                    <button
                        key={t.id}
                        onClick={() => onSelect(t.id)}
                        className={`group relative text-left rounded-lg border overflow-hidden transition-all ${active
                            ? "border-primary/60 ring-2 ring-primary/30"
                            : "border-border hover:border-foreground/30"
                            }`}
                    >
                        <div className="aspect-[80/110] bg-muted/40 text-foreground/80 p-1.5">
                            <img alt="Preview" src={`${process.env.NEXT_PUBLIC_API_URL}/static/previews/${t.preview}`} onError={(e) => {
                                e.currentTarget.src = "https://placehold.co/300x400?text=Not+Available";
                            }} />
                        </div>
                        {active && (
                            <div className="absolute top-1 right-1 w-4 h-4 rounded-full bg-primary text-primary-foreground flex items-center justify-center shadow">
                                <Check className="w-2.5 h-2.5" />
                            </div>
                        )}
                        <div className="p-2 border-t border-border bg-card">
                            <div className="flex items-center justify-between gap-1">
                                <span className="text-xs font-medium truncate">{t.name}</span>
                                {/* <span className="text-[9px] font-mono uppercase text-muted-foreground shrink-0">
                                        {t.category}
                                    </span> */}
                            </div>
                            {t.variants?.length > 0 && (
                                <RadioGroup defaultValue={selectedVariantId} className="flex flex-wrap gap-1 mt-4" onValueChange={(value) => onSelect(t.id, value)}>
                                    {t.variants.map((variant) => {
                                        return (
                                            <div key={variant.name}>
                                                <RadioGroupItem className="hidden" value={variant.id} id={variant.id} />
                                                {/* <Label className="text-[10px] cursor-pointer" htmlFor={variant.id}>{variant.name}</Label> */}
                                                <span
                                                    className="text-[9px] leading-none px-1.5 py-0.5 rounded bg-muted text-muted-foreground"
                                                >
                                                    {variant.name}
                                                </span>
                                            </div>
                                        );
                                    })}
                                </RadioGroup>
                            )}
                        </div>
                    </button>
                );
            })}
        </div>
    );
}
