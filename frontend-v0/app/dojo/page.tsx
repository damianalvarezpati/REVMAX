'use client';

import { useCallback, useEffect, useState } from 'react';
import { trainingCases, adjustmentDecisions } from '@/lib/mock-data';
import {
  getKnowledgeInputs,
  getValidationInbox,
  updateValidationInboxTask,
  type KnowledgeInputsResponse,
  type ValidationInboxFullResponse,
} from '@/lib/revmax-api';
import { cn } from '@/lib/utils';
import { 
  Swords, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  ThumbsUp,
  ThumbsDown,
  Star,
  Building2,
  ChevronLeft,
  ChevronRight,
  BarChart3,
  MessageSquare,
  Settings2,
  Inbox,
  AlertTriangle,
  ClipboardList,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

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

const demandConfig = {
  low: { label: 'Low', className: 'bg-red-100 text-red-700' },
  moderate: { label: 'Moderate', className: 'bg-amber-100 text-amber-700' },
  high: { label: 'High', className: 'bg-emerald-100 text-emerald-700' },
  'very-high': { label: 'Very High', className: 'bg-emerald-100 text-emerald-700' },
};

const knowledgeStatusClass: Record<string, string> = {
  weak: 'bg-red-100 text-red-800 border-red-200',
  developing: 'bg-amber-100 text-amber-900 border-amber-200',
  usable: 'bg-sky-100 text-sky-900 border-sky-200',
  strong: 'bg-emerald-100 text-emerald-900 border-emerald-200',
};

const apiConfigured =
  typeof process.env.NEXT_PUBLIC_REVMAX_API_URL === 'string' &&
  process.env.NEXT_PUBLIC_REVMAX_API_URL.length > 0;

interface CaseReview {
  agreement: 'agree' | 'partial' | 'disagree' | null;
  score: number;
  feedback: string;
  adjustment: string;
}

export default function DojoPage() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [reviews, setReviews] = useState<Record<string, CaseReview>>({});
  const [knowledge, setKnowledge] = useState<KnowledgeInputsResponse | null>(null);
  const [knowledgeErr, setKnowledgeErr] = useState<string | null>(null);
  const [inboxFull, setInboxFull] = useState<ValidationInboxFullResponse | null>(null);
  const [inboxErr, setInboxErr] = useState<string | null>(null);
  const [inboxActionId, setInboxActionId] = useState<string | null>(null);
  const [dismissNote, setDismissNote] = useState<Record<string, string>>({});

  const loadDojoData = useCallback(async () => {
    if (!apiConfigured) return;
    try {
      const [k, inv] = await Promise.all([
        getKnowledgeInputs(),
        getValidationInbox().catch(() => null),
      ]);
      setKnowledge(k);
      setKnowledgeErr(k.error ?? null);
      setInboxFull(inv);
      setInboxErr(null);
    } catch (e) {
      setKnowledge(null);
      setKnowledgeErr(e instanceof Error ? e.message : 'Knowledge Inputs API error');
    }
  }, [apiConfigured]);

  useEffect(() => {
    loadDojoData();
  }, [loadDojoData]);

  const handleInboxTask = async (taskId: string, status: 'done' | 'dismissed') => {
    if (!apiConfigured) return;
    setInboxActionId(taskId);
    setInboxErr(null);
    try {
      const dr = status === 'dismissed' ? (dismissNote[taskId] || '').trim() || undefined : undefined;
      await updateValidationInboxTask(taskId, { status, dismiss_reason: dr });
      await loadDojoData();
    } catch (e) {
      setInboxErr(e instanceof Error ? e.message : 'Error al actualizar tarea');
    } finally {
      setInboxActionId(null);
    }
  };

  const pendingInboxTasks =
    inboxFull?.inbox?.tasks?.filter((t) => (t.status || 'pending') === 'pending') ?? [];

  const currentCase = trainingCases[currentIndex];
  const currentReview = reviews[currentCase.id] || {
    agreement: null,
    score: 0,
    feedback: '',
    adjustment: ''
  };

  const updateReview = (updates: Partial<CaseReview>) => {
    setReviews(prev => ({
      ...prev,
      [currentCase.id]: { ...currentReview, ...updates }
    }));
  };

  const config = recommendationConfig[currentCase.recommendation];
  const Icon = config.icon;

  // Calculate summary stats
  const completedReviews = Object.values(reviews).filter(r => r.agreement !== null);
  const avgScore = completedReviews.length > 0 
    ? (completedReviews.reduce((sum, r) => sum + r.score, 0) / completedReviews.length).toFixed(1)
    : '—';
  const agreementRate = completedReviews.length > 0
    ? Math.round((completedReviews.filter(r => r.agreement === 'agree').length / completedReviews.length) * 100)
    : 0;

  return (
    <div className="flex gap-6">
      {/* Main Content */}
      <div className="flex-1 max-w-3xl space-y-6">
        {/* Header */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Swords className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-semibold tracking-tight">Dojo</h1>
          </div>
          <p className="text-muted-foreground">Review and validate AI recommendations to improve model accuracy</p>
        </div>

        {/* Bandeja operativa — deuda real (API validation-inbox) */}
        {apiConfigured && (
          <div className="rounded-2xl border border-amber-600/50 bg-amber-500/[0.07] p-4 space-y-3">
            <div className="flex items-center gap-2">
              <ClipboardList className="h-5 w-5 text-amber-800 dark:text-amber-300" />
              <h2 className="text-sm font-semibold text-foreground">Operativa — bandeja Dojo</h2>
              <span className="text-xs text-muted-foreground">(tareas obligatorias, no sugerencias)</span>
            </div>
            {inboxErr && <p className="text-xs text-destructive">{inboxErr}</p>}
            {pendingInboxTasks.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No hay tareas pendientes en el inbox, o aún no se ha sincronizado. Ejecuta Knowledge Inputs / refresh en
                backend para generar deuda.
              </p>
            ) : (
              <ul className="space-y-3 max-h-72 overflow-auto text-xs">
                {pendingInboxTasks.map((t) => (
                  <li
                    key={t.task_id}
                    className="rounded-lg border border-border/60 bg-background/80 p-3 space-y-2"
                  >
                    <div className="flex flex-wrap gap-2 items-start justify-between">
                      <div>
                        <span className="font-mono text-[10px] text-muted-foreground">{t.task_type}</span>
                        <span className="text-muted-foreground"> · </span>
                        <span className="font-medium">{t.area_key}</span>
                        {t.required_for_area_progress && (
                          <span className="ml-2 text-[10px] uppercase text-amber-700 dark:text-amber-400">
                            requerido
                          </span>
                        )}
                      </div>
                      <div className="flex gap-1 shrink-0">
                        <Button
                          type="button"
                          size="sm"
                          variant="default"
                          className="h-7 text-[11px]"
                          disabled={inboxActionId === t.task_id}
                          onClick={() => handleInboxTask(t.task_id, 'done')}
                        >
                          {inboxActionId === t.task_id ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            'Hecho'
                          )}
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="h-7 text-[11px]"
                          disabled={inboxActionId === t.task_id}
                          onClick={() => handleInboxTask(t.task_id, 'dismissed')}
                        >
                          Descartar
                        </Button>
                      </div>
                    </div>
                    <p className="text-muted-foreground leading-snug">{t.reason}</p>
                    <input
                      type="text"
                      placeholder="Motivo si descartas (trazabilidad)"
                      className="w-full rounded-md border border-input bg-background px-2 py-1 text-[11px]"
                      value={dismissNote[t.task_id] ?? ''}
                      onChange={(e) =>
                        setDismissNote((prev) => ({ ...prev, [t.task_id]: e.target.value }))
                      }
                    />
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* Knowledge Inputs — materia prima por área (API admin_panel) */}
        <div className="rounded-2xl border border-border/60 bg-muted/20 p-4 space-y-3">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-primary" />
            <h2 className="text-sm font-semibold">Knowledge Inputs</h2>
            <span className="text-xs text-muted-foreground">(madurez: datasets · reglas · validación · motor PRO)</span>
          </div>
          {!apiConfigured && (
            <p className="text-xs text-muted-foreground">
              Configura <code className="rounded bg-muted px-1">NEXT_PUBLIC_REVMAX_API_URL</code> para cargar scores en vivo.
            </p>
          )}
          {apiConfigured && knowledgeErr && (
            <p className="text-xs text-destructive">{knowledgeErr}</p>
          )}
          {apiConfigured && knowledge?.knowledge_refresh?.finished_at && (
            <div className="rounded-lg border border-dashed border-border/60 bg-background/50 px-3 py-2 text-xs text-muted-foreground space-y-1">
              <p className="font-medium text-foreground">Último Knowledge Refresh</p>
              <p>
                {knowledge.knowledge_refresh.finished_at} · modo {knowledge.knowledge_refresh.mode ?? '—'} · run{' '}
                <code className="text-[10px]">{knowledge.knowledge_refresh.run_id?.slice(0, 8) ?? '—'}</code>
              </p>
              <p>
                Áreas: {(knowledge.knowledge_refresh.areas_reviewed ?? []).join(', ') || '—'} · observados{' '}
                {knowledge.knowledge_refresh.observed_count ?? 0} · candidatos Dojo{' '}
                {knowledge.knowledge_refresh.dojo_candidates_created ?? 0}
              </p>
              {(knowledge.knowledge_refresh.funnel_metrics ||
                knowledge.knowledge_refresh.funnel_lifetime) && (
                <p className="text-[11px] pt-1 border-t border-border/40">
                  Funnel: aceptados tot.{' '}
                  {(knowledge.knowledge_refresh.funnel_metrics as { accepted_total?: number } | undefined)
                    ?.accepted_total ??
                    (knowledge.knowledge_refresh.funnel_lifetime as { accepted_total?: number } | undefined)
                      ?.accepted_total ??
                    '—'}{' '}
                  · tasa{' '}
                  {(knowledge.knowledge_refresh.funnel_metrics as { acceptance_rate?: number } | undefined)
                    ?.acceptance_rate ??
                    (knowledge.knowledge_refresh.funnel_lifetime as { acceptance_rate?: number } | undefined)
                      ?.acceptance_rate ??
                    '—'}{' '}
                  · runs c/ delta{' '}
                  {(knowledge.knowledge_refresh.funnel_metrics as { runs_with_delta_count?: number } | undefined)
                    ?.runs_with_delta_count ??
                    (knowledge.knowledge_refresh.funnel_lifetime as { runs_with_delta_count?: number } | undefined)
                      ?.runs_with_delta_count ??
                    '—'}{' '}
                  · Dojo validados{' '}
                  {(knowledge.knowledge_refresh.funnel_metrics as { dojo_candidates_validated?: number } | undefined)
                    ?.dojo_candidates_validated ??
                    (knowledge.knowledge_refresh.funnel_lifetime as { dojo_candidates_validated?: number } | undefined)
                      ?.dojo_candidates_validated ??
                    '—'}
                </p>
              )}
            </div>
          )}
          {apiConfigured && knowledge?.dojo_validation_inbox?.global_metrics && (
            <div className="rounded-lg border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-xs space-y-2">
              <div className="flex items-center gap-2 font-semibold text-amber-900 dark:text-amber-200">
                <Inbox className="h-4 w-4 shrink-0" />
                Bandeja obligatoria — deuda de validación
              </div>
              <p className="text-muted-foreground">
                Pendientes:{' '}
                <span className="font-mono text-foreground">
                  {knowledge.dojo_validation_inbox.global_metrics.dojo_inbox_count ?? 0}
                </span>{' '}
                · atrasados:{' '}
                <span className="font-mono text-foreground">
                  {knowledge.dojo_validation_inbox.global_metrics.overdue_reviews_count ?? 0}
                </span>{' '}
                · áreas bloqueadas:{' '}
                <span className="font-mono text-foreground">
                  {knowledge.dojo_validation_inbox.global_metrics.areas_blocked_count ?? 0}
                </span>
              </p>
              <p className="text-[10px] text-muted-foreground border-t border-amber-500/20 pt-2">
                Acciones sobre tareas: bloque <span className="font-medium text-foreground">Operativa — bandeja Dojo</span>{' '}
                arriba.
              </p>
            </div>
          )}
          {apiConfigured && knowledge?.areas && knowledge.areas.length > 0 && (
            <div className="max-h-56 overflow-auto rounded-lg border border-border/50 bg-card text-xs">
              <table className="w-full border-collapse">
                <thead className="sticky top-0 bg-muted/80 backdrop-blur">
                  <tr className="text-left text-muted-foreground">
                    <th className="p-2 font-medium">Área</th>
                    <th className="p-2 font-medium">Score</th>
                    <th className="p-2 font-medium">Estado</th>
                    <th className="p-2 font-medium hidden sm:table-cell">Deuda</th>
                    <th className="p-2 font-medium hidden sm:table-cell">DS</th>
                    <th className="p-2 font-medium hidden sm:table-cell">Reglas</th>
                    <th className="p-2 font-medium hidden md:table-cell">Huecos</th>
                  </tr>
                </thead>
                <tbody>
                  {knowledge.areas.map((a) => (
                    <tr key={a.area_key} className="border-t border-border/40">
                      <td className="p-2 font-medium">
                        <span className="inline-flex items-center gap-1">
                          {a.area_blocked_by_validation && (
                            <AlertTriangle className="h-3 w-3 text-amber-600 shrink-0" title="Bloqueada por validación" />
                          )}
                          {a.area_name}
                        </span>
                      </td>
                      <td className="p-2 tabular-nums">{a.area_score}</td>
                      <td className="p-2">
                        <span
                          className={cn(
                            'inline-flex rounded-md border px-1.5 py-0.5 text-[10px] font-semibold uppercase',
                            knowledgeStatusClass[a.status_label] || 'bg-muted text-muted-foreground',
                          )}
                        >
                          {a.status_label}
                        </span>
                      </td>
                      <td className="p-2 tabular-nums hidden sm:table-cell text-muted-foreground" title={`validation_debt_score: ${a.validation_debt_score ?? 0}`}>
                        {a.validation_debt_score != null ? Math.round(a.validation_debt_score) : '—'}
                      </td>
                      <td className="p-2 tabular-nums hidden sm:table-cell">{a.datasets_count}</td>
                      <td className="p-2 tabular-nums hidden sm:table-cell">{a.rules_supported_count}</td>
                      <td className="p-2 text-muted-foreground hidden md:table-cell max-w-[200px] truncate" title={a.missing_gaps.join(' · ')}>
                        {a.missing_gaps[0] || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="rounded-lg border border-dashed border-border/60 px-3 py-2 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Demo (mock)</span> — casos de práctica locales; no sustituyen la
          bandeja ni qa_runs reales.
        </div>

        {/* Case Navigation */}
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
            disabled={currentIndex === 0}
          >
            <ChevronLeft className="h-4 w-4 mr-2" />
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Case {currentIndex + 1} of {trainingCases.length}
          </span>
          <Button
            variant="outline"
            onClick={() => setCurrentIndex(Math.min(trainingCases.length - 1, currentIndex + 1))}
            disabled={currentIndex === trainingCases.length - 1}
          >
            Next
            <ChevronRight className="h-4 w-4 ml-2" />
          </Button>
        </div>

        {/* Case Card */}
        <div className="rounded-2xl bg-card p-6 shadow-sm border border-border/50">
          {/* Hotel Info */}
          <div className="flex items-center gap-3 mb-6">
            <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <Building2 className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h2 className="font-semibold">{currentCase.hotelName}</h2>
              <p className="text-sm text-muted-foreground">Training Case #{currentCase.id}</p>
            </div>
          </div>

          {/* Metrics Grid */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="text-center p-4 rounded-xl bg-secondary/50">
              <p className="text-xs text-muted-foreground mb-1">Current Price</p>
              <p className="text-xl font-semibold">€{currentCase.currentPrice}</p>
            </div>
            <div className="text-center p-4 rounded-xl bg-secondary/50">
              <p className="text-xs text-muted-foreground mb-1">Market Avg</p>
              <p className="text-xl font-semibold">€{currentCase.marketAverage}</p>
            </div>
            <div className="text-center p-4 rounded-xl bg-secondary/50">
              <p className="text-xs text-muted-foreground mb-1">Demand</p>
              <span className={cn(
                'inline-flex items-center rounded-lg px-2 py-0.5 text-sm font-medium',
                demandConfig[currentCase.demandLevel].className
              )}>
                {demandConfig[currentCase.demandLevel].label}
              </span>
            </div>
            <div className="text-center p-4 rounded-xl bg-secondary/50">
              <p className="text-xs text-muted-foreground mb-1">Confidence</p>
              <p className="text-xl font-semibold">{currentCase.confidence}%</p>
            </div>
          </div>

          {/* Recommendation */}
          <div className={cn(
            'rounded-xl border p-4 mb-6',
            config.className
          )}>
            <div className="flex items-center gap-3">
              <Icon className="h-6 w-6" />
              <div>
                <p className="text-xs font-medium opacity-70">AI Recommendation</p>
                <p className="text-lg font-semibold capitalize">{currentCase.recommendation} Price</p>
              </div>
            </div>
          </div>

          {/* Reasoning */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-2">
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
              <p className="text-sm font-medium">AI Reasoning</p>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {currentCase.reasoning}
            </p>
          </div>

          {/* Review Controls */}
          <div className="space-y-6 pt-6 border-t border-border">
            {/* Agreement */}
            <div>
              <p className="text-sm font-medium mb-3">Do you agree with this recommendation?</p>
              <div className="flex gap-2">
                {([
                  { value: 'agree', label: 'Agree', icon: ThumbsUp, className: 'hover:bg-emerald-50 hover:border-emerald-200 hover:text-emerald-700' },
                  { value: 'partial', label: 'Partial', icon: Minus, className: 'hover:bg-amber-50 hover:border-amber-200 hover:text-amber-700' },
                  { value: 'disagree', label: 'Disagree', icon: ThumbsDown, className: 'hover:bg-red-50 hover:border-red-200 hover:text-red-700' },
                ] as const).map((option) => {
                  const OptionIcon = option.icon;
                  const isSelected = currentReview.agreement === option.value;
                  return (
                    <button
                      key={option.value}
                      onClick={() => updateReview({ agreement: option.value })}
                      className={cn(
                        'flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl border transition-all',
                        isSelected 
                          ? option.value === 'agree' 
                            ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                            : option.value === 'partial'
                            ? 'bg-amber-50 border-amber-200 text-amber-700'
                            : 'bg-red-50 border-red-200 text-red-700'
                          : 'bg-secondary/50 border-transparent',
                        option.className
                      )}
                    >
                      <OptionIcon className="h-4 w-4" />
                      {option.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Score */}
            <div>
              <p className="text-sm font-medium mb-3">Quality Score (1-5)</p>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((score) => (
                  <button
                    key={score}
                    onClick={() => updateReview({ score })}
                    className={cn(
                      'flex items-center justify-center w-12 h-12 rounded-xl border transition-all',
                      currentReview.score === score
                        ? 'bg-primary text-primary-foreground border-primary'
                        : 'bg-secondary/50 border-transparent hover:bg-secondary'
                    )}
                  >
                    <Star className={cn(
                      'h-5 w-5',
                      currentReview.score >= score ? 'fill-current' : ''
                    )} />
                  </button>
                ))}
              </div>
            </div>

            {/* Feedback */}
            <div>
              <p className="text-sm font-medium mb-3">Feedback</p>
              <Textarea
                placeholder="Add your feedback or notes about this case..."
                value={currentReview.feedback}
                onChange={(e) => updateReview({ feedback: e.target.value })}
                rows={3}
              />
            </div>

            {/* Adjustment Decision */}
            <div>
              <p className="text-sm font-medium mb-3">Recommended Adjustment</p>
              <Select
                value={currentReview.adjustment}
                onValueChange={(value) => updateReview({ adjustment: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select adjustment type..." />
                </SelectTrigger>
                <SelectContent>
                  {adjustmentDecisions.map((decision) => (
                    <SelectItem key={decision.value} value={decision.value}>
                      {decision.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Submit */}
            <Button className="w-full" disabled={!currentReview.agreement}>
              Submit Review
            </Button>
          </div>
        </div>
      </div>

      {/* Summary Panel */}
      <div className="w-72 shrink-0">
        <div className="rounded-2xl bg-card p-5 shadow-sm border border-border/50 sticky top-8">
          <div className="flex items-center gap-2 mb-6">
            <BarChart3 className="h-5 w-5 text-primary" />
            <h3 className="font-semibold">Session Summary</h3>
          </div>

          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-secondary/50">
              <p className="text-xs text-muted-foreground mb-1">Reviewed</p>
              <p className="text-2xl font-semibold">{completedReviews.length} / {trainingCases.length}</p>
            </div>
            
            <div className="p-4 rounded-xl bg-secondary/50">
              <p className="text-xs text-muted-foreground mb-1">Average Score</p>
              <p className="text-2xl font-semibold">{avgScore}</p>
            </div>
            
            <div className="p-4 rounded-xl bg-secondary/50">
              <p className="text-xs text-muted-foreground mb-1">Agreement Rate</p>
              <p className="text-2xl font-semibold">{agreementRate}%</p>
            </div>

            {completedReviews.length > 0 && (
              <div className="p-4 rounded-xl bg-primary/5 border border-primary/10">
                <div className="flex items-center gap-2 mb-2">
                  <Settings2 className="h-4 w-4 text-primary" />
                  <p className="text-xs font-medium">Recommended Action</p>
                </div>
                <p className="text-sm text-muted-foreground">
                  {agreementRate >= 80 
                    ? 'Model performing well. No immediate changes needed.'
                    : agreementRate >= 60
                    ? 'Consider reviewing threshold settings.'
                    : 'Significant review of model rules recommended.'
                  }
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
