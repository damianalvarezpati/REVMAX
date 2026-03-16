'use client';

import { useEffect, useState } from 'react';
import { AnalysisStep, statusMessages } from '@/lib/mock-data';
import { cn } from '@/lib/utils';
import { Check, Loader2, AlertTriangle, X, Clock } from 'lucide-react';

interface ProgressPanelProps {
  steps: AnalysisStep[];
  isRunning?: boolean;
}

const statusConfig = {
  done: { icon: Check, className: 'bg-emerald-500 text-white' },
  active: { icon: Loader2, className: 'bg-primary text-primary-foreground animate-pulse' },
  warning: { icon: AlertTriangle, className: 'bg-amber-500 text-white' },
  error: { icon: X, className: 'bg-red-500 text-white' },
  pending: { icon: Clock, className: 'bg-muted text-muted-foreground' },
};

export function ProgressPanel({ steps, isRunning }: ProgressPanelProps) {
  const [currentMessage, setCurrentMessage] = useState(statusMessages[0]);

  useEffect(() => {
    if (isRunning) {
      const interval = setInterval(() => {
        const randomIndex = Math.floor(Math.random() * statusMessages.length);
        setCurrentMessage(statusMessages[randomIndex]);
      }, 1500);
      return () => clearInterval(interval);
    }
  }, [isRunning]);

  return (
    <div className="rounded-2xl bg-card p-5 shadow-sm border border-border/50">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold">Analysis Progress</h3>
        {steps.every(s => s.status === 'done') && (
          <span className="text-xs text-emerald-600 font-medium">Complete</span>
        )}
      </div>

      {/* Status Message */}
      {isRunning && (
        <div className="mb-4 p-3 rounded-xl bg-primary/5 border border-primary/10">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 text-primary animate-spin" />
            <span className="text-sm text-foreground">{currentMessage}</span>
          </div>
        </div>
      )}

      {/* Steps */}
      <div className="space-y-1">
        {steps.map((step, index) => {
          const config = statusConfig[step.status];
          const Icon = config.icon;
          const isLast = index === steps.length - 1;

          return (
            <div key={step.id} className="relative">
              <div className="flex items-start gap-3 py-2">
                {/* Icon */}
                <div className={cn(
                  'relative z-10 flex h-6 w-6 items-center justify-center rounded-full shrink-0',
                  config.className
                )}>
                  <Icon className={cn(
                    'h-3.5 w-3.5',
                    step.status === 'active' && 'animate-spin'
                  )} />
                </div>
                
                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p className={cn(
                    'text-sm font-medium truncate',
                    step.status === 'pending' ? 'text-muted-foreground' : 'text-foreground'
                  )}>
                    {step.name}
                  </p>
                  {step.message && (
                    <p className="text-xs text-amber-600 mt-0.5">{step.message}</p>
                  )}
                </div>
              </div>

              {/* Connector Line */}
              {!isLast && (
                <div className={cn(
                  'absolute left-[11px] top-8 h-[calc(100%-16px)] w-0.5',
                  step.status === 'done' ? 'bg-emerald-200' : 'bg-border'
                )} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
