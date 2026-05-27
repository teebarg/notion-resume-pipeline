"use client";

import { cn } from "@/lib/utils";
import { templates, type TemplateId } from "@/lib/resume-types";
import { Check } from "lucide-react";
import React, { useState, useEffect } from "react";

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
                console.log("🚀 ~ fetchTemplates ~ response:", response);

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
                    <button
                        key={template.id}
                        onClick={() => onSelect(template.id)}
                        className={`w-full text-left p-3 rounded-lg border transition-all ${
                            isTemplateSelected
                                ? "border-primary/60 bg-primary/5 ring-1 ring-primary/20"
                                : "border-border hover:border-foreground/20 bg-card"
                        }`}
                    >
                        <div className="flex items-center justify-between">
                            <span className="text-sm font-medium">{template.name}</span>
                            {isTemplateSelected && <Check className="w-3.5 h-3.5 text-primary" />}
                        </div>
                        <div className="text-xs text-muted-foreground mt-0.5">{template.description}</div>
                    </button>
                );

                return (
                    <div
                        key={template.id}
                        className={`border rounded-2xl p-5 bg-white flex flex-col justify-between transition-all duration-200 ${
                            isTemplateSelected ? "ring-2 ring-blue-600 border-transparent shadow-md" : "border-slate-200 hover:shadow-lg"
                        }`}
                    >
                        <div>
                            <h3 className="font-bold text-slate-900 text-lg tracking-tight">{template.name}</h3>
                            <p className="text-slate-500 text-xs mt-1 leading-relaxed mb-4">{template.description}</p>
                        </div>

                        <div>
                            {/* Dynamic Design Variant Swatches */}
                            {template.variants?.length > 0 && (
                                <div className="mb-4">
                                    <span className="text-[10px] uppercase tracking-wider font-bold text-slate-400 block mb-2">Color Themes</span>
                                    <div className="flex gap-2">
                                        {template.variants.map((variant) => {
                                            const isVariantSelected = selectedVariantId === variant.id && isTemplateSelected;
                                            return (
                                                <button
                                                    key={variant.id}
                                                    type="button"
                                                    onClick={() => onSelect(template.id, variant.id)}
                                                    title={`${template.name} (${variant.name})`}
                                                    // Tailwind maps custom dynamically injected bg configurations safely or maps to standard hex styles
                                                    className={`w-6 h-6 rounded-full border-2 hover:scale-110 transition-transform ${
                                                        isVariantSelected ? "border-blue-600 scale-105" : "border-transparent"
                                                    }`}
                                                    style={{
                                                        backgroundColor: variant.primary_color.includes("-") ? undefined : variant.primary_color,
                                                    }}
                                                    // Supports both tailwind color classes (if whitelisted) or raw hex colors
                                                />
                                            );
                                        })}
                                    </div>
                                </div>
                            )}

                            {/* Selection Trigger */}
                            <button
                                type="button"
                                onClick={() => onSelect(template.id, template.variants?.[0]?.id)}
                                className={`w-full py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                                    isTemplateSelected ? "bg-blue-50 text-blue-700" : "bg-slate-900 text-white hover:bg-slate-800"
                                }`}
                            >
                                {isTemplateSelected ? "Selected Design" : "Select Layout"}
                            </button>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
