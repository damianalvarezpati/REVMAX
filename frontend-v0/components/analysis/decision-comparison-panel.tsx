'use client';

import { FileCode2, AlertTriangle, CheckCircle2 } from 'lucide-react';

import type { DecisionComparison } from '@/lib/revmax-api';

function Badge({
  match,
}: {
  match: boolean;
}) {
  if (match) {
    return (
      <div className="inline-flex items-center rounded-md bg-emerald-100 border border-emerald-200 text-emerald-800 px-2 py-0.5 text-xs font-medium w-fit">
        <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
        MATCH
      </div>
    );
  }

  return (
    <div className="inline-flex items-center rounded-md bg-amber-100 border border-amber-200 text-amber-900 px-2 py-0.5 text-xs font-medium w-fit">
      <AlertTriangle className="h-3.5 w-3.5 mr-1" />
      MISMATCH
    </div>
  );
}

function renderList(items?: string[], max = 6) {
  if (!items || !items.length) return <span className="text-xs text-muted-foreground">—</span>;
  const shown = items.slice(0, max);
  return (
    <div className="space-y-1">
      {shown.map((t, i) => (
        <div key={i} className="text-xs text-foreground/90">
          • {t}
        </div>
      ))}
      {items.length > max && <div className="text-xs text-muted-foreground">… +{items.length - max} más</div>}
    </div>
  );
}

export function DecisionComparisonPanel({ comparison }: { comparison: DecisionComparison }) {
  const match = comparison.match ?? false;

  return (
    <div className="rounded-2xl bg-card p-4 shadow-sm border border-border/50">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <FileCode2 className="h-5 w-5 text-primary" />
          <div>
            <h3 className="text-sm font-semibold leading-tight">Internal Audit: Legacy vs PRO</h3>
            <p className="text-xs text-muted-foreground">Comparación solo para revisión técnica.</p>
          </div>
        </div>
        <Badge match={match} />
      </div>

      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="rounded-xl bg-secondary/40 border border-border/50 p-3">
          <p className="text-xs text-muted-foreground mb-1">Legacy decision</p>
          <p className="text-sm font-semibold">{comparison.legacy_decision ?? 'unknown'}</p>
        </div>
        <div className="rounded-xl bg-secondary/40 border border-border/50 p-3">
          <p className="text-xs text-muted-foreground mb-1">PRO decision</p>
          <p className="text-sm font-semibold">{comparison.deterministic_pro_decision ?? 'unknown'}</p>
        </div>
      </div>

      <div className="mb-3">
        <p className="text-xs text-muted-foreground mb-1">difference_type</p>
        <p className="text-sm font-medium">{comparison.difference_type ?? 'unknown_difference'}</p>
      </div>

      {comparison.comment && (
        <div className="mb-3 p-3 rounded-xl bg-secondary/30 border border-border/50">
          <p className="text-xs text-muted-foreground mb-1">comment</p>
          <p className="text-xs text-foreground/90">{comparison.comment}</p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-border/50 p-3 bg-secondary/20">
          <p className="text-xs text-muted-foreground mb-1">pro_reasons</p>
          {renderList(comparison.pro_reasons, 6)}
        </div>
        <div className="rounded-xl border border-border/50 p-3 bg-secondary/20">
          <p className="text-xs text-muted-foreground mb-1">constraints_applied</p>
          {renderList(comparison.constraints_applied, 6)}
        </div>
      </div>

      {!!comparison.missing_data?.length && (
        <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-3">
          <p className="text-xs text-amber-900 font-medium mb-1">missing_data</p>
          {renderList(comparison.missing_data, 6)}
        </div>
      )}
    </div>
  );
}

