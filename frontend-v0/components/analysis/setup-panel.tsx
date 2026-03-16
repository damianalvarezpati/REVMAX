'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { Play, AlertTriangle, Globe, Building2 } from 'lucide-react';
import { Spinner } from '@/components/ui/spinner';

/** Props para conectar Analysis al backend real (sin mocks de hotel). */
export interface SetupPanelProps {
  hotelName: string;
  city: string;
  fastDemo: boolean;
  onHotelNameChange: (value: string) => void;
  onCityChange: (value: string) => void;
  onFastDemoChange: (value: boolean) => void;
  onRunAnalysis: () => void;
  isRunning: boolean;
  errorMessage?: string | null;
  currentJobHotel?: string | null;
}

export function SetupPanel({
  hotelName,
  city,
  fastDemo,
  onHotelNameChange,
  onCityChange,
  onFastDemoChange,
  onRunAnalysis,
  isRunning,
  errorMessage,
  currentJobHotel,
}: SetupPanelProps) {
  return (
    <div className="rounded-2xl bg-card p-5 shadow-sm border border-border/50">
      <h3 className="text-sm font-semibold mb-4">Analysis Setup</h3>

      <div className="space-y-3 mb-5">
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">Hotel name</label>
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-muted-foreground shrink-0" />
            <Input
              placeholder="e.g. Catalonia Berlin Mitte"
              value={hotelName}
              onChange={(e) => onHotelNameChange(e.target.value)}
              disabled={isRunning}
              className="flex-1"
            />
          </div>
        </div>
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">City (optional)</label>
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4 text-muted-foreground shrink-0" />
            <Input
              placeholder="e.g. Berlin"
              value={city}
              onChange={(e) => onCityChange(e.target.value)}
              disabled={isRunning}
              className="flex-1"
            />
          </div>
        </div>
        {currentJobHotel && (
          <p className="text-xs text-muted-foreground">Running: {currentJobHotel}</p>
        )}
      </div>

      <div className="mb-5">
        <p className="text-sm text-muted-foreground mb-2">Mode</p>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onFastDemoChange(false)}
            className={cn(
              'flex-1 px-3 py-2 rounded-xl text-sm font-medium transition-all',
              !fastDemo ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
            )}
          >
            Standard
          </button>
          <button
            type="button"
            onClick={() => onFastDemoChange(true)}
            className={cn(
              'flex-1 px-3 py-2 rounded-xl text-sm font-medium transition-all',
              fastDemo ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
            )}
          >
            Demo
          </button>
        </div>
      </div>

      {fastDemo && (
        <div className="mb-5 p-3 rounded-xl bg-amber-50 border border-amber-200">
          <div className="flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
            <p className="text-xs text-amber-700">
              Demo mode — faster run, no full scraping or complete market analysis
            </p>
          </div>
        </div>
      )}

      {errorMessage && (
        <div className="mb-5 p-3 rounded-xl bg-destructive/10 border border-destructive/20">
          <p className="text-xs text-destructive">{errorMessage}</p>
        </div>
      )}

      <Button className="w-full" onClick={onRunAnalysis} disabled={isRunning}>
        {isRunning ? (
          <>
            <Spinner className="h-4 w-4 mr-2" />
            Running Analysis...
          </>
        ) : (
          <>
            <Play className="h-4 w-4 mr-2" />
            Run Analysis
          </>
        )}
      </Button>
    </div>
  );
}
