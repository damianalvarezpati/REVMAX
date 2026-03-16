'use client';

import { 
  dashboardMetrics, 
  latestSignals, 
  hotels, 
  analysisResults,
  alerts
} from '@/lib/mock-data';
import { 
  BarChart3, 
  Percent, 
  AlertTriangle, 
  Lightbulb, 
  Building2,
  TrendingUp,
  TrendingDown,
  Minus,
  Activity,
  Zap,
  CheckCircle2
} from 'lucide-react';
import { cn } from '@/lib/utils';
import Link from 'next/link';

const signalTypeConfig = {
  demand: { icon: TrendingUp, className: 'text-emerald-600 bg-emerald-50' },
  competitor: { icon: Building2, className: 'text-blue-600 bg-blue-50' },
  parity: { icon: AlertTriangle, className: 'text-amber-600 bg-amber-50' },
  event: { icon: Zap, className: 'text-purple-600 bg-purple-50' },
};

const recommendationIcon = {
  raise: TrendingUp,
  hold: Minus,
  lower: TrendingDown,
};

const recommendationClass = {
  raise: 'text-emerald-600',
  hold: 'text-blue-600',
  lower: 'text-amber-600',
};

export default function DashboardPage() {
  // Get hotels that need attention (have alerts)
  const hotelsNeedingAttention = hotels.filter(h => 
    alerts.some(a => a.hotelId === h.id && a.status !== 'resolved')
  );

  // Get top recommendations
  const topRecommendations = Object.values(analysisResults)
    .filter(a => a.recommendation !== 'hold')
    .slice(0, 3);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">Your revenue intelligence at a glance</p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          icon={BarChart3}
          label="Analyses Today"
          value={dashboardMetrics.analysesToday}
          trend="+12%"
          trendUp
        />
        <MetricCard
          icon={Percent}
          label="Avg Confidence"
          value={`${dashboardMetrics.avgConfidence}%`}
          trend="+3%"
          trendUp
        />
        <MetricCard
          icon={AlertTriangle}
          label="Active Alerts"
          value={dashboardMetrics.revenueAlerts}
          trend="-2"
          trendUp
        />
        <MetricCard
          icon={Lightbulb}
          label="Opportunities"
          value={dashboardMetrics.opportunitiesFound}
          trend="+5"
          trendUp
        />
        <MetricCard
          icon={Building2}
          label="Needs Attention"
          value={dashboardMetrics.hotelsNeedingAttention}
          warning={dashboardMetrics.hotelsNeedingAttention > 0}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Latest Signals */}
        <div className="lg:col-span-2 rounded-2xl bg-card p-6 shadow-sm border border-border/50">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold">Latest Signals</h2>
            <Link href="/alerts" className="text-sm text-primary hover:underline">
              View all
            </Link>
          </div>
          <div className="space-y-4">
            {latestSignals.map((signal) => {
              const config = signalTypeConfig[signal.type as keyof typeof signalTypeConfig];
              const Icon = config.icon;
              return (
                <div
                  key={signal.id}
                  className="flex items-start gap-4 p-4 rounded-xl bg-secondary/30 hover:bg-secondary/50 transition-colors"
                >
                  <div className={cn(
                    'flex h-10 w-10 items-center justify-center rounded-xl shrink-0',
                    config.className
                  )}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground">{signal.message}</p>
                    <p className="text-xs text-muted-foreground mt-1">{signal.timestamp}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* System Quality */}
        <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
          <h2 className="text-lg font-semibold mb-6">System Quality</h2>
          <div className="space-y-4">
            <QualityItem label="API Response" value={98} />
            <QualityItem label="Data Freshness" value={95} />
            <QualityItem label="Parity Coverage" value={92} />
            <QualityItem label="Compset Accuracy" value={88} />
          </div>
          <div className="mt-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              <span className="text-sm font-medium text-emerald-700">All systems operational</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Top Recommendations */}
        <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold">Top Recommendations Today</h2>
            <Link href="/" className="text-sm text-primary hover:underline">
              View all
            </Link>
          </div>
          <div className="space-y-4">
            {topRecommendations.map((analysis) => {
              const hotel = hotels.find(h => h.id === analysis.hotelId);
              const Icon = recommendationIcon[analysis.recommendation];
              return (
                <Link
                  key={analysis.hotelId}
                  href="/"
                  className="flex items-center justify-between p-4 rounded-xl bg-secondary/30 hover:bg-secondary/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-xl bg-background flex items-center justify-center">
                      <Building2 className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">{hotel?.name}</p>
                      <p className="text-xs text-muted-foreground">{hotel?.city}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Icon className={cn('h-5 w-5', recommendationClass[analysis.recommendation])} />
                    <span className={cn('text-sm font-medium capitalize', recommendationClass[analysis.recommendation])}>
                      {analysis.recommendation}
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>

        {/* Hotels Needing Attention */}
        <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold">Hotels Needing Attention</h2>
            <Link href="/alerts" className="text-sm text-primary hover:underline">
              View alerts
            </Link>
          </div>
          {hotelsNeedingAttention.length > 0 ? (
            <div className="space-y-4">
              {hotelsNeedingAttention.map((hotel) => {
                const hotelAlerts = alerts.filter(a => a.hotelId === hotel.id && a.status !== 'resolved');
                return (
                  <Link
                    key={hotel.id}
                    href="/alerts"
                    className="flex items-center justify-between p-4 rounded-xl bg-amber-50 border border-amber-200 hover:bg-amber-100 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-xl bg-amber-100 flex items-center justify-center">
                        <AlertTriangle className="h-5 w-5 text-amber-600" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-foreground">{hotel.name}</p>
                        <p className="text-xs text-amber-700">{hotelAlerts.length} active alert{hotelAlerts.length !== 1 ? 's' : ''}</p>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-8">
              <div className="mx-auto w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center mb-4">
                <CheckCircle2 className="h-6 w-6 text-emerald-600" />
              </div>
              <p className="text-sm text-muted-foreground">All hotels are performing well</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface MetricCardProps {
  icon: React.ElementType;
  label: string;
  value: string | number;
  trend?: string;
  trendUp?: boolean;
  warning?: boolean;
}

function MetricCard({ icon: Icon, label, value, trend, trendUp, warning }: MetricCardProps) {
  return (
    <div className={cn(
      'rounded-2xl bg-card p-5 shadow-sm border transition-all duration-300 hover:shadow-md hover:-translate-y-0.5',
      warning ? 'border-amber-200 bg-amber-50/50' : 'border-border/50'
    )}>
      <div className="flex items-center gap-2 mb-3">
        <Icon className={cn('h-4 w-4', warning ? 'text-amber-600' : 'text-muted-foreground')} />
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
      <div className="flex items-end justify-between">
        <span className="text-2xl font-semibold">{value}</span>
        {trend && (
          <span className={cn(
            'text-xs font-medium',
            trendUp ? 'text-emerald-600' : 'text-red-600'
          )}>
            {trend}
          </span>
        )}
      </div>
    </div>
  );
}

interface QualityItemProps {
  label: string;
  value: number;
}

function QualityItem({ label, value }: QualityItemProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{value}%</span>
      </div>
      <div className="h-2 w-full rounded-full bg-secondary overflow-hidden">
        <div 
          className={cn(
            'h-full rounded-full transition-all duration-500',
            value >= 90 ? 'bg-emerald-500' : value >= 80 ? 'bg-blue-500' : 'bg-amber-500'
          )}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}
