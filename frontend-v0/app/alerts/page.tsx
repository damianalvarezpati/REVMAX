'use client';

import { useState } from 'react';
import { alerts } from '@/lib/mock-data';
import { cn } from '@/lib/utils';
import { 
  Bell, 
  AlertTriangle, 
  AlertCircle, 
  Info,
  Filter,
  CheckCircle2,
  Clock,
  Building2,
  ChevronRight,
  X
} from 'lucide-react';
import { Button } from '@/components/ui/button';

const severityConfig = {
  critical: { 
    icon: AlertCircle, 
    label: 'Critical',
    className: 'bg-red-50 border-red-200 text-red-700',
    iconClass: 'text-red-600 bg-red-100',
    badgeClass: 'bg-red-100 text-red-700'
  },
  high: { 
    icon: AlertTriangle, 
    label: 'High',
    className: 'bg-amber-50 border-amber-200 text-amber-700',
    iconClass: 'text-amber-600 bg-amber-100',
    badgeClass: 'bg-amber-100 text-amber-700'
  },
  medium: { 
    icon: Info, 
    label: 'Medium',
    className: 'bg-blue-50 border-blue-200 text-blue-700',
    iconClass: 'text-blue-600 bg-blue-100',
    badgeClass: 'bg-blue-100 text-blue-700'
  },
};

const statusConfig = {
  new: { label: 'New', className: 'bg-red-100 text-red-700' },
  acknowledged: { label: 'Acknowledged', className: 'bg-amber-100 text-amber-700' },
  resolved: { label: 'Resolved', className: 'bg-emerald-100 text-emerald-700' },
};

const typeLabels = {
  parity_violation: 'Parity Violation',
  weak_demand: 'Weak Demand',
  underpricing: 'Underpricing',
  visibility_issue: 'Visibility Issue',
  competitor_pressure: 'Competitor Pressure',
};

export default function AlertsPage() {
  const [severityFilter, setSeverityFilter] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  const filteredAlerts = alerts.filter(alert => {
    const matchesSeverity = !severityFilter || alert.severity === severityFilter;
    const matchesStatus = !statusFilter || alert.status === statusFilter;
    return matchesSeverity && matchesStatus;
  });

  // Group by severity
  const criticalAlerts = filteredAlerts.filter(a => a.severity === 'critical');
  const highAlerts = filteredAlerts.filter(a => a.severity === 'high');
  const mediumAlerts = filteredAlerts.filter(a => a.severity === 'medium');

  const alertGroups = [
    { severity: 'critical' as const, alerts: criticalAlerts },
    { severity: 'high' as const, alerts: highAlerts },
    { severity: 'medium' as const, alerts: mediumAlerts },
  ].filter(g => g.alerts.length > 0);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Alerts</h1>
          <p className="text-muted-foreground mt-1">Revenue alerts and action items</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            {alerts.filter(a => a.status !== 'resolved').length} active alerts
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Severity:</span>
          <div className="flex gap-1">
            {(['critical', 'high', 'medium'] as const).map((severity) => {
              const config = severityConfig[severity];
              return (
                <button
                  key={severity}
                  onClick={() => setSeverityFilter(severityFilter === severity ? null : severity)}
                  className={cn(
                    'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                    severityFilter === severity
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                  )}
                >
                  {config.label}
                </button>
              );
            })}
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Status:</span>
          <div className="flex gap-1">
            {(['new', 'acknowledged', 'resolved'] as const).map((status) => {
              const config = statusConfig[status];
              return (
                <button
                  key={status}
                  onClick={() => setStatusFilter(statusFilter === status ? null : status)}
                  className={cn(
                    'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors capitalize',
                    statusFilter === status
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                  )}
                >
                  {config.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Alert Groups */}
      <div className="space-y-8">
        {alertGroups.map(({ severity, alerts: groupAlerts }) => {
          const config = severityConfig[severity];
          const Icon = config.icon;
          
          return (
            <div key={severity}>
              <div className="flex items-center gap-2 mb-4">
                <div className={cn('p-1.5 rounded-lg', config.iconClass)}>
                  <Icon className="h-4 w-4" />
                </div>
                <h2 className="text-lg font-semibold">{config.label}</h2>
                <span className="text-sm text-muted-foreground">({groupAlerts.length})</span>
              </div>
              
              <div className="space-y-3">
                {groupAlerts.map((alert) => {
                  const alertStatus = statusConfig[alert.status];
                  return (
                    <div
                      key={alert.id}
                      className={cn(
                        'group rounded-2xl border p-5 transition-all duration-300 hover:shadow-md',
                        config.className
                      )}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-4">
                          <div className={cn('p-2.5 rounded-xl shrink-0', config.iconClass)}>
                            <Icon className="h-5 w-5" />
                          </div>
                          <div>
                            <div className="flex items-center gap-3 mb-1">
                              <h3 className="font-semibold">{alert.title}</h3>
                              <span className={cn(
                                'inline-flex items-center rounded-lg px-2 py-0.5 text-xs font-medium',
                                alertStatus.className
                              )}>
                                {alertStatus.label}
                              </span>
                            </div>
                            <p className="text-sm opacity-80 mb-2">
                              {alert.description}
                            </p>
                            <div className="flex items-center gap-4 text-xs opacity-70">
                              <span className="flex items-center gap-1">
                                <Building2 className="h-3.5 w-3.5" />
                                {alert.hotelName}
                              </span>
                              <span className="flex items-center gap-1">
                                <Clock className="h-3.5 w-3.5" />
                                {new Date(alert.timestamp).toLocaleString()}
                              </span>
                              <span className="capitalize">
                                {typeLabels[alert.type]}
                              </span>
                            </div>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          {alert.status !== 'resolved' && (
                            <>
                              <Button variant="ghost" size="sm" className="h-8">
                                <CheckCircle2 className="h-4 w-4 mr-1" />
                                Resolve
                              </Button>
                              <Button variant="ghost" size="icon" className="h-8 w-8">
                                <X className="h-4 w-4" />
                              </Button>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {filteredAlerts.length === 0 && (
        <div className="text-center py-12">
          <div className="mx-auto w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center mb-4">
            <CheckCircle2 className="h-6 w-6 text-emerald-600" />
          </div>
          <p className="text-muted-foreground">No alerts matching your filters</p>
        </div>
      )}
    </div>
  );
}
