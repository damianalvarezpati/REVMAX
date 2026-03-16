'use client';

import { use } from 'react';
import { useRouter } from 'next/navigation';
import { reports } from '@/lib/mock-data';
import { cn } from '@/lib/utils';
import { 
  ArrowLeft, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  Calendar,
  Download,
  Share2,
  BarChart3,
  Activity,
  Calendar as CalendarIcon,
  Globe,
  Lightbulb,
  Shield
} from 'lucide-react';
import { Button } from '@/components/ui/button';

const recommendationConfig = {
  raise: { 
    label: 'RAISE PRICE', 
    icon: TrendingUp, 
    bgClass: 'bg-gradient-to-br from-emerald-50 to-teal-50',
    borderClass: 'border-emerald-200/60',
    textClass: 'text-emerald-700',
    badgeClass: 'bg-emerald-100 text-emerald-700' 
  },
  hold: { 
    label: 'HOLD PRICE', 
    icon: Minus, 
    bgClass: 'bg-gradient-to-br from-blue-50 to-indigo-50',
    borderClass: 'border-blue-200/60',
    textClass: 'text-blue-700',
    badgeClass: 'bg-blue-100 text-blue-700' 
  },
  lower: { 
    label: 'LOWER PRICE', 
    icon: TrendingDown, 
    bgClass: 'bg-gradient-to-br from-amber-50 to-orange-50',
    borderClass: 'border-amber-200/60',
    textClass: 'text-amber-700',
    badgeClass: 'bg-amber-100 text-amber-700' 
  },
};

export default function ReportDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const { id } = use(params);
  const report = reports.find(r => r.id === id);

  if (!report) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground">Report not found</p>
      </div>
    );
  }

  const config = recommendationConfig[report.recommendation];
  const Icon = config.icon;

  const formattedDate = new Date(report.date).toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{report.hotelName}</h1>
            <p className="text-muted-foreground mt-1 flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              {formattedDate}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            <Share2 className="h-4 w-4 mr-2" />
            Share
          </Button>
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Download PDF
          </Button>
        </div>
      </div>

      {/* Recommendation Hero */}
      <div className={cn(
        'relative overflow-hidden rounded-2xl border p-8',
        config.bgClass,
        config.borderClass
      )}>
        <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-white/30 blur-3xl" />
        
        <div className="relative">
          <div className={cn(
            'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold tracking-wide mb-4',
            config.badgeClass
          )}>
            RECOMMENDATION
          </div>
          <div className="flex items-center gap-4 mb-4">
            <Icon className={cn('h-10 w-10', config.textClass)} strokeWidth={2} />
            <h2 className={cn('text-3xl font-bold tracking-tight', config.textClass)}>
              {config.label}
            </h2>
          </div>
          <div className="flex items-center gap-3 mb-4">
            <div className="h-2 w-32 rounded-full bg-white/60 overflow-hidden">
              <div 
                className={cn('h-full rounded-full', config.textClass.replace('text', 'bg'))}
                style={{ width: `${report.confidence}%` }}
              />
            </div>
            <span className={cn('text-sm font-medium', config.textClass)}>
              Confidence: {report.confidence}%
            </span>
          </div>
        </div>
      </div>

      {/* Executive Summary */}
      <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
        <h3 className="text-lg font-semibold mb-4">Executive Summary</h3>
        <p className="text-muted-foreground leading-relaxed">
          {report.executiveSummary}
        </p>
      </div>

      {/* Price Comparison */}
      <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
        <div className="flex items-center gap-2 mb-6">
          <BarChart3 className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold">Price Comparison</h3>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-4 rounded-xl bg-secondary/50">
            <p className="text-sm text-muted-foreground mb-1">Your Price</p>
            <p className="text-3xl font-semibold">€{report.priceComparison.yourPrice}</p>
          </div>
          <div className="text-center p-4 rounded-xl bg-secondary/50">
            <p className="text-sm text-muted-foreground mb-1">Market Average</p>
            <p className="text-3xl font-semibold">€{report.priceComparison.marketAverage}</p>
          </div>
          <div className="text-center p-4 rounded-xl bg-secondary/50">
            <p className="text-sm text-muted-foreground mb-1">Position</p>
            <p className="text-3xl font-semibold">{report.priceComparison.position}</p>
          </div>
        </div>
      </div>

      {/* Market Demand */}
      <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold">Market Demand</h3>
        </div>
        <p className="text-muted-foreground leading-relaxed">
          {report.marketDemand}
        </p>
      </div>

      {/* Events */}
      <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
        <div className="flex items-center gap-2 mb-4">
          <CalendarIcon className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold">Events</h3>
        </div>
        {report.events.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {report.events.map((event, index) => (
              <span
                key={index}
                className="inline-flex items-center rounded-xl bg-primary/5 px-4 py-2 text-sm font-medium border border-primary/10"
              >
                {event}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No significant events detected.</p>
        )}
      </div>

      {/* Distribution & Parity */}
      <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
        <div className="flex items-center gap-2 mb-4">
          <Globe className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold">Distribution & Parity</h3>
        </div>
        <p className="text-muted-foreground leading-relaxed">
          {report.distributionParity}
        </p>
      </div>

      {/* Suggested Action */}
      <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
        <div className="flex items-center gap-2 mb-4">
          <Lightbulb className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold">Suggested Action</h3>
        </div>
        <div className="p-4 rounded-xl bg-primary/5 border border-primary/10">
          <p className="text-foreground font-medium">
            {report.suggestedAction}
          </p>
        </div>
      </div>

      {/* Confidence & Limits */}
      <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold">Confidence & Limitations</h3>
        </div>
        <p className="text-muted-foreground leading-relaxed">
          {report.confidenceLimits}
        </p>
      </div>
    </div>
  );
}
