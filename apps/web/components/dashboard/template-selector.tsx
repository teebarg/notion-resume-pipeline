'use client'

import { cn } from '@/lib/utils'
import { templates, type TemplateId } from '@/lib/resume-types'
import { Check } from 'lucide-react'

interface TemplateSelectorProps {
  selected: TemplateId
  onSelect: (id: TemplateId) => void
}

const templateStyles: Record<TemplateId, { accent: string; bg: string }> = {
  minimal: { accent: 'bg-foreground/10', bg: 'bg-muted/50' },
  modern: { accent: 'bg-blue-500/20', bg: 'bg-blue-500/5' },
  classic: { accent: 'bg-amber-500/20', bg: 'bg-amber-500/5' },
  developer: { accent: 'bg-emerald-500/20', bg: 'bg-emerald-500/5' },
}

export function TemplateSelector({ selected, onSelect }: TemplateSelectorProps) {
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-muted-foreground">Template</h3>
      <div className="grid grid-cols-2 gap-3">
        {templates?.map((template) => {
          const isSelected = selected === template.id
          const styles = templateStyles[template.id]
          
          return (
            <button
              key={template.id}
              onClick={() => onSelect(template.id)}
              className={cn(
                'group relative flex flex-col items-start rounded-lg border p-3 text-left transition-all hover:border-foreground/20',
                isSelected
                  ? 'border-foreground/30 bg-accent'
                  : 'border-border bg-card'
              )}
            >
              {isSelected && (
                <div className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full bg-foreground">
                  <Check className="h-3 w-3 text-background" />
                </div>
              )}
              
              {/* Template preview mini */}
              <div className={cn(
                'mb-2 flex h-16 w-full flex-col gap-1 rounded border p-2',
                styles.bg
              )}>
                <div className={cn('h-2 w-3/4 rounded-sm', styles.accent)} />
                <div className={cn('h-1.5 w-1/2 rounded-sm', styles.accent, 'opacity-60')} />
                <div className="mt-auto flex gap-1">
                  <div className={cn('h-1 w-1/4 rounded-sm', styles.accent, 'opacity-40')} />
                  <div className={cn('h-1 w-1/3 rounded-sm', styles.accent, 'opacity-40')} />
                </div>
              </div>
              
              <span className="text-sm font-medium">{template.name}</span>
              <span className="text-xs text-muted-foreground line-clamp-1">
                {template.description}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
