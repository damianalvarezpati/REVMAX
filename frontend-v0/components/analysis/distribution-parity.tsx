'use client';

import { cn } from '@/lib/utils';
import { CheckCircle2, AlertTriangle, XCircle, Globe } from 'lucide-react';

interface DistributionParityProps {
  status: 'ok' | 'warning' | 'violation';
  channels: string[];
  message: string;
}

const statusConfig = {
  ok: {
    icon: CheckCircle2,
    label: 'OK',
    className: 'text-emerald-600 bg-emerald-50',
    borderClass: 'border-emerald-200',
  },
  warning: {
    icon: AlertTriangle,
    label: 'Warning',
    className: 'text-amber-600 bg-amber-50',
    borderClass: 'border-amber-200',
  },
  violation: {
    icon: XCircle,
    label: 'Violation',
    className: 'text-red-600 bg-red-50',
    borderClass: 'border-red-200',
  },
};

export function DistributionParity({ status, channels, message }: DistributionParityProps) {
  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
      <div className="flex items-center gap-2 mb-4">
        <Globe className="h-5 w-5 text-primary" />
        <h3 className="text-lg font-semibold">Distribution & Parity</h3>
      </div>

      <div className="flex items-center gap-4 mb-4">
        <div className={cn(
          'inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium border',
          config.className,
          config.borderClass
        )}>
          <Icon className="h-4 w-4" />
          Parity Status: {config.label}
        </div>
      </div>

      <div className="mb-4">
        <p className="text-sm text-muted-foreground mb-2">Channels checked:</p>
        <div className="flex flex-wrap gap-2">
          {channels.map((channel, index) => (
            <span
              key={index}
              className="inline-flex items-center rounded-lg bg-secondary px-3 py-1.5 text-sm text-secondary-foreground"
            >
              {channel}
            </span>
          ))}
        </div>
      </div>

      <p className="text-sm text-muted-foreground">
        {message}
      </p>
    </div>
  );
}
