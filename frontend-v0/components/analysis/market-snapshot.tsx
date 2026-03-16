'use client';

import { AnalysisResult } from '@/lib/mock-data';
import { Euro, BarChart3, Hash, TrendingUp, Star, Eye } from 'lucide-react';

interface MarketSnapshotProps {
  analysis: AnalysisResult;
}

interface MetricBlockProps {
  icon: React.ElementType;
  label: string;
  value: string | number;
  note?: string;
  prefix?: string;
  suffix?: string;
}

function MetricBlock({ icon: Icon, label, value, note, prefix, suffix }: MetricBlockProps) {
  return (
    <div className="group relative overflow-hidden rounded-2xl bg-card p-6 shadow-sm border border-border/50 transition-all duration-300 hover:shadow-md hover:-translate-y-0.5">
      <div className="absolute -right-4 -top-4 h-16 w-16 rounded-full bg-primary/5 transition-transform duration-300 group-hover:scale-150" />
      <div className="relative">
        <div className="flex items-center gap-2 mb-3">
          <Icon className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium text-muted-foreground">{label}</span>
        </div>
        <div className="flex items-baseline gap-1">
          {prefix && <span className="text-lg text-muted-foreground">{prefix}</span>}
          <span className="text-3xl font-semibold tracking-tight">{value}</span>
          {suffix && <span className="text-lg text-muted-foreground">{suffix}</span>}
        </div>
        {note && (
          <p className="mt-2 text-xs text-muted-foreground">{note}</p>
        )}
      </div>
    </div>
  );
}

export function MarketSnapshot({ analysis }: MarketSnapshotProps) {
  const visibilityLabel = {
    low: 'Low',
    medium: 'Medium',
    high: 'High'
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Market Snapshot</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <MetricBlock
          icon={Euro}
          label="Your Price"
          value={analysis.yourPrice}
          suffix="€"
          note="Standard Double Room"
        />
        <MetricBlock
          icon={BarChart3}
          label="Market Average"
          value={analysis.marketAverage}
          suffix="€"
          note="Comparable hotels"
        />
        <MetricBlock
          icon={Hash}
          label="Price Position"
          value={`#${analysis.pricePosition.rank}`}
          suffix={`/ ${analysis.pricePosition.total}`}
          note={analysis.pricePosition.rank <= 3 ? 'Competitive position' : 'Higher than average'}
        />
        <MetricBlock
          icon={TrendingUp}
          label="Demand Index"
          value={analysis.demandIndex}
          note={analysis.demandIndex > 70 ? 'Strong demand' : analysis.demandIndex > 50 ? 'Moderate demand' : 'Soft demand'}
        />
        <MetricBlock
          icon={Star}
          label="Reputation"
          value={analysis.reputation}
          note="Guest review score"
        />
        <MetricBlock
          icon={Eye}
          label="Visibility"
          value={visibilityLabel[analysis.visibility]}
          note="Search ranking strength"
        />
      </div>
    </div>
  );
}
