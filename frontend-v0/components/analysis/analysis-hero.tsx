'use client';

import { AnalysisResult } from '@/lib/mock-data';
import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus, Clock } from 'lucide-react';

interface AnalysisHeroProps {
  analysis: AnalysisResult;
}

const recommendationConfig = {
  raise: {
    label: 'RAISE PRICE',
    icon: TrendingUp,
    bgClass: 'bg-gradient-to-br from-emerald-50 to-teal-50',
    borderClass: 'border-emerald-200/60',
    textClass: 'text-emerald-700',
    badgeClass: 'bg-emerald-100 text-emerald-700',
  },
  hold: {
    label: 'HOLD PRICE',
    icon: Minus,
    bgClass: 'bg-gradient-to-br from-blue-50 to-indigo-50',
    borderClass: 'border-blue-200/60',
    textClass: 'text-blue-700',
    badgeClass: 'bg-blue-100 text-blue-700',
  },
  lower: {
    label: 'LOWER PRICE',
    icon: TrendingDown,
    bgClass: 'bg-gradient-to-br from-amber-50 to-orange-50',
    borderClass: 'border-amber-200/60',
    textClass: 'text-amber-700',
    badgeClass: 'bg-amber-100 text-amber-700',
  },
};

const demandConfig = {
  low: { label: 'Low', className: 'bg-red-100 text-red-700' },
  moderate: { label: 'Moderate', className: 'bg-amber-100 text-amber-700' },
  high: { label: 'High', className: 'bg-emerald-100 text-emerald-700' },
  'very-high': { label: 'Very High', className: 'bg-emerald-100 text-emerald-700' },
};

const parityConfig = {
  ok: { label: 'OK', className: 'bg-emerald-100 text-emerald-700' },
  warning: { label: 'Warning', className: 'bg-amber-100 text-amber-700' },
  violation: { label: 'Violation', className: 'bg-red-100 text-red-700' },
};

export function AnalysisHero({ analysis }: AnalysisHeroProps) {
  const config = recommendationConfig[analysis.recommendation];
  const Icon = config.icon;

  return (
    <div className={cn(
      'relative overflow-hidden rounded-2xl border p-8',
      config.bgClass,
      config.borderClass
    )}>
      {/* Background decoration */}
      <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-white/30 blur-3xl" />
      <div className="absolute -bottom-10 -left-10 h-40 w-40 rounded-full bg-white/20 blur-2xl" />
      
      <div className="relative">
        {/* Badge */}
        <div className={cn(
          'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold tracking-wide mb-6',
          config.badgeClass
        )}>
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-current" />
          </span>
          REVMAX RECOMMENDS
        </div>

        {/* Main Recommendation */}
        <div className="flex items-center gap-4 mb-4">
          <Icon className={cn('h-12 w-12', config.textClass)} strokeWidth={2} />
          <h2 className={cn('text-4xl font-bold tracking-tight', config.textClass)}>
            {config.label}
          </h2>
        </div>

        {/* Confidence */}
        <div className="flex items-center gap-3 mb-4">
          <div className="h-2 w-32 rounded-full bg-white/60 overflow-hidden">
            <div 
              className={cn('h-full rounded-full', config.textClass.replace('text', 'bg'))}
              style={{ width: `${analysis.confidence}%` }}
            />
          </div>
          <span className={cn('text-sm font-medium', config.textClass)}>
            Confidence: {analysis.confidence}%
          </span>
        </div>

        {/* Summary */}
        <p className="text-base text-foreground/80 leading-relaxed max-w-2xl mb-6">
          {analysis.summary}
        </p>

        {/* Quick Stats */}
        <div className="flex flex-wrap gap-2">
          <span className={cn(
            'inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium',
            demandConfig[analysis.demandLevel].className
          )}>
            Demand: {demandConfig[analysis.demandLevel].label}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/60 px-3 py-1.5 text-sm font-medium text-foreground/80">
            Position: {analysis.pricePosition.rank} / {analysis.pricePosition.total}
          </span>
          <span className={cn(
            'inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium',
            parityConfig[analysis.parityStatus].className
          )}>
            Parity: {parityConfig[analysis.parityStatus].label}
          </span>
        </div>

        {/* Last Analysis */}
        <div className="mt-6 flex items-center gap-1.5 text-sm text-foreground/60">
          <Clock className="h-3.5 w-3.5" />
          Last analysis run: {analysis.lastAnalysisRun}
        </div>
      </div>
    </div>
  );
}
