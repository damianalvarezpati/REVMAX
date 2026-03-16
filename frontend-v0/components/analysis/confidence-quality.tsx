'use client';

import { cn } from '@/lib/utils';
import { Shield, Info } from 'lucide-react';

interface ConfidenceQualityProps {
  quality: 'excellent' | 'good' | 'degraded' | 'poor';
  confidence: number;
  fallbackCount: number;
  note: string;
}

const qualityConfig = {
  excellent: { label: 'Excellent', className: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
  good: { label: 'Good', className: 'bg-blue-100 text-blue-700 border-blue-200' },
  degraded: { label: 'Degraded', className: 'bg-amber-100 text-amber-700 border-amber-200' },
  poor: { label: 'Poor', className: 'bg-red-100 text-red-700 border-red-200' },
};

export function ConfidenceQuality({ quality, confidence, fallbackCount, note }: ConfidenceQualityProps) {
  const config = qualityConfig[quality];

  return (
    <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
      <div className="flex items-center gap-2 mb-4">
        <Shield className="h-5 w-5 text-primary" />
        <h3 className="text-lg font-semibold">Confidence & Data Quality</h3>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center p-4 rounded-xl bg-secondary/50">
          <p className="text-sm text-muted-foreground mb-1">Quality</p>
          <span className={cn(
            'inline-flex items-center rounded-lg px-3 py-1 text-sm font-medium border',
            config.className
          )}>
            {config.label}
          </span>
        </div>
        <div className="text-center p-4 rounded-xl bg-secondary/50">
          <p className="text-sm text-muted-foreground mb-1">Confidence</p>
          <p className="text-2xl font-semibold">{confidence}%</p>
        </div>
        <div className="text-center p-4 rounded-xl bg-secondary/50">
          <p className="text-sm text-muted-foreground mb-1">Fallbacks</p>
          <p className="text-2xl font-semibold">{fallbackCount}</p>
        </div>
      </div>

      <div className="flex items-start gap-2 p-3 rounded-xl bg-secondary/30">
        <Info className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
        <p className="text-sm text-muted-foreground">{note}</p>
      </div>
    </div>
  );
}
