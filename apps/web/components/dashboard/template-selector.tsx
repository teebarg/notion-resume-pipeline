'use client'

import { cn } from '@/lib/utils'
import { templates, type TemplateId } from '@/lib/resume-types'
import { Check } from 'lucide-react'
import React, { useState, useEffect } from 'react';

// 1. Define types matching the backend Pydantic schemas
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

const templateStyles: Record<TemplateId, { accent: string; bg: string }> = {
  minimal: { accent: 'bg-foreground/10', bg: 'bg-muted/50' },
  modern: { accent: 'bg-blue-500/20', bg: 'bg-blue-500/5' },
  classic: { accent: 'bg-amber-500/20', bg: 'bg-amber-500/5' },
  developer: { accent: 'bg-emerald-500/20', bg: 'bg-emerald-500/5' },
  "modern-sidebar": { accent: 'bg-red-500/20', bg: 'bg-red-500/5' },
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
        setError(err instanceof Error ? err.message : 'An unexpected error occurred');
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
        <span className="ml-3 text-gray-600 font-medium">Loading premium templates...</span>
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
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
      {templates.map((template) => {
        const isTemplateSelected = selectedTemplateId === template.id;

        return (
          <div
            key={template.id}
            className={`border rounded-2xl p-5 bg-white flex flex-col justify-between transition-all duration-200 ${isTemplateSelected
              ? 'ring-2 ring-blue-600 border-transparent shadow-md'
              : 'border-slate-200 hover:shadow-lg'
              }`}
          >
            <div>
              {/* Fallback layout wrapper for image previews */}
              <div className="bg-slate-100 rounded-xl aspect-[3/4] mb-4 overflow-hidden flex items-center justify-center border border-slate-100">
                <img
                  src={`/assets/previews/${template.preview}`}
                  alt={`${template.name} preview`}
                  className="w-full h-full object-cover object-top"
                  onError={(e) => {
                    // Fallback placeholder if layout thumbnail is missing
                    (e.target as HTMLImageElement).src = 'https://placehold.co/300x400?text=Preview+Coming+Soon';
                  }}
                />
              </div>

              <h3 className="font-bold text-slate-900 text-lg tracking-tight">{template.name}</h3>
              <p className="text-slate-500 text-xs mt-1 leading-relaxed mb-4">{template.description}</p>
            </div>

            <div>
              {/* Dynamic Design Variant Swatches */}
              {template.variants.length > 0 && (
                <div className="mb-4">
                  <span className="text-[10px] uppercase tracking-wider font-bold text-slate-400 block mb-2">
                    Color Themes
                  </span>
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
                          className={`w-6 h-6 rounded-full border-2 hover:scale-110 transition-transform ${isVariantSelected ? 'border-blue-600 scale-105' : 'border-transparent'
                            }`}
                          style={{ backgroundColor: variant.primary_color.includes('-') ? undefined : variant.primary_color }}
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
                onClick={() => onSelect(template.id, template.variants[0]?.id)}
                className={`w-full py-2.5 rounded-xl text-sm font-semibold transition-colors ${isTemplateSelected
                  ? 'bg-blue-50 text-blue-700'
                  : 'bg-slate-900 text-white hover:bg-slate-800'
                  }`}
              >
                {isTemplateSelected ? 'Selected Design' : 'Select Layout'}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
  // return (
  //   <div className="space-y-3">
  //     <h3 className="text-sm font-medium text-muted-foreground">Template</h3>
  //     <div className="grid grid-cols-2 gap-3">
  //       {templates?.map((template) => {
  //         const isSelected = selected === template.id
  //         const styles = templateStyles[template.id]

  //         return (
  //           <button
  //             key={template.id}
  //             onClick={() => onSelect(template.id)}
  //             className={cn(
  //               'group relative flex flex-col items-start rounded-lg border p-3 text-left transition-all hover:border-foreground/20',
  //               isSelected
  //                 ? 'border-foreground/30 bg-accent'
  //                 : 'border-border bg-card'
  //             )}
  //           >
  //             {isSelected && (
  //               <div className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full bg-foreground">
  //                 <Check className="h-3 w-3 text-background" />
  //               </div>
  //             )}

  //             {/* Template preview mini */}
  //             <div className={cn(
  //               'mb-2 flex h-16 w-full flex-col gap-1 rounded border p-2',
  //               styles.bg
  //             )}>
  //               <div className={cn('h-2 w-3/4 rounded-sm', styles.accent)} />
  //               <div className={cn('h-1.5 w-1/2 rounded-sm', styles.accent, 'opacity-60')} />
  //               <div className="mt-auto flex gap-1">
  //                 <div className={cn('h-1 w-1/4 rounded-sm', styles.accent, 'opacity-40')} />
  //                 <div className={cn('h-1 w-1/3 rounded-sm', styles.accent, 'opacity-40')} />
  //               </div>
  //             </div>

  //             <span className="text-sm font-medium">{template.name}</span>
  //             <span className="text-xs text-muted-foreground line-clamp-1">
  //               {template.description}
  //             </span>
  //           </button>
  //         )
  //       })}
  //     </div>
  //   </div>
  // )
}
