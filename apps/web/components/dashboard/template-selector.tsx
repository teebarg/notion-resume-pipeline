"use client";

import { Check } from "lucide-react";
import { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
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
                <span className="ml-3 text-gray-600 font-medium text-sm">Loading premium templates...</span>
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
        <div className="grid grid-cols-1 p-2 gap-2">
            {templates.map((template) => {
                const isTemplateSelected = selectedTemplateId === template.id;
                return (
                    <div
                        key={template.id}
                        onClick={() => onSelect(template.id)}
                        className={`w-full text-left p-3 rounded-lg border transition-all ${isTemplateSelected
                            ? "border-primary/60 bg-primary/5 ring-1 ring-primary/20"
                            : "border-border hover:border-foreground/20 bg-card"
                            }`}
                    >
                        <div className="flex items-center justify-between">
                            <span className="text-sm font-medium">{template.name}</span>
                            {isTemplateSelected && <Check className="w-3.5 h-3.5 text-primary" />}
                        </div>
                        <div className="text-xs text-muted-foreground mt-0.5">{template.description}</div>
                        {template.variants?.length > 0 && (
                            <RadioGroup defaultValue={selectedVariantId} className="flex mt-4" onValueChange={(value) => onSelect(template.id, value)}>
                                {template.variants.map((variant) => {
                                    return (
                                        <div>
                                            <RadioGroupItem className="hidden" value={variant.id} id={variant.id} />
                                            <Label className="text-[10px] cursor-pointer" htmlFor={variant.id}>{variant.name}</Label>
                                        </div>
                                    );
                                })}
                            </RadioGroup>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
