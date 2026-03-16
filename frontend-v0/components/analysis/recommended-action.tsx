'use client';

import { Lightbulb, ChevronRight } from 'lucide-react';

interface RecommendedActionProps {
  summary: string;
  bullets: string[];
}

export function RecommendedAction({ summary, bullets }: RecommendedActionProps) {
  return (
    <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
      <div className="flex items-center gap-2 mb-4">
        <Lightbulb className="h-5 w-5 text-primary" />
        <h3 className="text-lg font-semibold">Recommended Action</h3>
      </div>

      <p className="text-base text-muted-foreground leading-relaxed mb-6">
        {summary}
      </p>

      <div className="space-y-3">
        {bullets.map((bullet, index) => (
          <div
            key={index}
            className="flex items-start gap-3 p-3 rounded-xl bg-primary/5 border border-primary/10"
          >
            <ChevronRight className="h-5 w-5 text-primary shrink-0 mt-0.5" />
            <span className="text-sm font-medium text-foreground">{bullet}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
