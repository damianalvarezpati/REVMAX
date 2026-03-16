'use client';

import { Calendar, Sparkles } from 'lucide-react';

interface EventsDetectedProps {
  events: string[];
}

export function EventsDetected({ events }: EventsDetectedProps) {
  return (
    <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
      <div className="flex items-center gap-2 mb-4">
        <Calendar className="h-5 w-5 text-primary" />
        <h3 className="text-lg font-semibold">Events Detected</h3>
      </div>
      
      {events.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {events.map((event, index) => (
            <div
              key={index}
              className="inline-flex items-center gap-2 rounded-xl bg-primary/5 px-4 py-2.5 text-sm font-medium text-foreground border border-primary/10"
            >
              <Sparkles className="h-4 w-4 text-primary" />
              {event}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          No major demand events detected in your area.
        </p>
      )}
    </div>
  );
}
