'use client';

import { useState } from 'react';
import { reports } from '@/lib/mock-data';
import { cn } from '@/lib/utils';
import { 
  FileText, 
  Calendar, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  ChevronRight,
  Filter,
  Building2
} from 'lucide-react';
import Link from 'next/link';

const recommendationConfig = {
  raise: { 
    label: 'Raise', 
    icon: TrendingUp, 
    className: 'bg-emerald-100 text-emerald-700 border-emerald-200' 
  },
  hold: { 
    label: 'Hold', 
    icon: Minus, 
    className: 'bg-blue-100 text-blue-700 border-blue-200' 
  },
  lower: { 
    label: 'Lower', 
    icon: TrendingDown, 
    className: 'bg-amber-100 text-amber-700 border-amber-200' 
  },
};

export default function ReportsPage() {
  const [filterRecommendation, setFilterRecommendation] = useState<string | null>(null);

  const filteredReports = reports.filter(report => 
    !filterRecommendation || report.recommendation === filterRecommendation
  );

  // Group reports by date
  const groupedReports = filteredReports.reduce((acc, report) => {
    const date = new Date(report.date).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
    if (!acc[date]) acc[date] = [];
    acc[date].push(report);
    return acc;
  }, {} as Record<string, typeof reports>);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Reports</h1>
        <p className="text-muted-foreground mt-1">History of analysis recommendations</p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <div className="flex gap-1">
          <button
            onClick={() => setFilterRecommendation(null)}
            className={cn(
              'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
              !filterRecommendation
                ? 'bg-primary text-primary-foreground'
                : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
            )}
          >
            All
          </button>
          {(['raise', 'hold', 'lower'] as const).map((rec) => {
            const config = recommendationConfig[rec];
            const Icon = config.icon;
            return (
              <button
                key={rec}
                onClick={() => setFilterRecommendation(filterRecommendation === rec ? null : rec)}
                className={cn(
                  'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors capitalize',
                  filterRecommendation === rec
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                {config.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Reports by Date */}
      <div className="space-y-8">
        {Object.entries(groupedReports).map(([date, dateReports]) => (
          <div key={date}>
            <div className="flex items-center gap-2 mb-4">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-medium text-muted-foreground">{date}</h2>
            </div>
            <div className="space-y-4">
              {dateReports.map((report) => {
                const config = recommendationConfig[report.recommendation];
                const Icon = config.icon;
                return (
                  <Link
                    key={report.id}
                    href={`/reports/${report.id}`}
                    className="group block rounded-2xl bg-card p-6 shadow-sm border border-border/50 hover:shadow-md hover:border-primary/20 transition-all duration-300"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-4">
                        <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                          <FileText className="h-6 w-6 text-primary" />
                        </div>
                        <div>
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="font-semibold group-hover:text-primary transition-colors">
                              {report.hotelName}
                            </h3>
                            <span className={cn(
                              'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium border',
                              config.className
                            )}>
                              <Icon className="h-3.5 w-3.5" />
                              {config.label} Price
                            </span>
                          </div>
                          <p className="text-sm text-muted-foreground line-clamp-2 max-w-2xl">
                            {report.executiveSummary}
                          </p>
                          <div className="flex items-center gap-4 mt-3">
                            <span className="text-xs text-muted-foreground">
                              Confidence: {report.confidence}%
                            </span>
                            <span className="text-xs text-muted-foreground">
                              Price: €{report.priceComparison.yourPrice} vs €{report.priceComparison.marketAverage} market avg
                            </span>
                          </div>
                        </div>
                      </div>
                      <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all shrink-0" />
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {filteredReports.length === 0 && (
        <div className="text-center py-12">
          <div className="mx-auto w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4">
            <FileText className="h-6 w-6 text-muted-foreground" />
          </div>
          <p className="text-muted-foreground">No reports found</p>
        </div>
      )}
    </div>
  );
}
