'use client';

import { MessageSquare } from 'lucide-react';

interface MarketContextProps {
  context: string;
}

export function MarketContext({ context }: MarketContextProps) {
  return (
    <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
      <div className="flex items-center gap-2 mb-4">
        <MessageSquare className="h-5 w-5 text-primary" />
        <h3 className="text-lg font-semibold">Market Context</h3>
      </div>
      <p className="text-base text-muted-foreground leading-relaxed">
        {context}
      </p>
    </div>
  );
}
