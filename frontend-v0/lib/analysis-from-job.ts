/**
 * Mapea la respuesta del backend (job-status) al formato que esperan los
 * componentes de Analysis (AnalysisResult de mock-data).
 * Solo para la pantalla Analysis; el resto del proyecto sigue usando mocks.
 */

import type { AnalysisResult, AnalysisStep, Competitor } from '@/lib/mock-data';
import type { JobStatusResponse, ProgressStep } from './revmax-api';

const NA = 'No encontrado';

function safeStr(val: unknown): string {
  if (val == null || val === '') return NA;
  return String(val);
}

function recommendationFromAction(action: string | undefined): 'raise' | 'hold' | 'lower' {
  const a = (action || '').toLowerCase();
  if (a === 'raise') return 'raise';
  if (a === 'lower') return 'lower';
  return 'hold';
}

function parityStatusFromString(s: string | undefined): 'ok' | 'warning' | 'violation' {
  const t = (s || '').toLowerCase();
  if (t.includes('violation') || t.includes('violación')) return 'violation';
  if (t.includes('warn') || t.includes('aviso')) return 'warning';
  return 'ok';
}

function visibilityFromString(s: string | undefined): 'low' | 'medium' | 'high' {
  const t = (s || '').toLowerCase();
  if (t.includes('high') || t.includes('alta')) return 'high';
  if (t.includes('low') || t.includes('baja')) return 'low';
  return 'medium';
}

function demandLevelFromScore(score: string | number | undefined): 'low' | 'moderate' | 'high' | 'very-high' {
  const n = typeof score === 'number' ? score : parseFloat(String(score ?? 0));
  if (Number.isNaN(n)) return 'moderate';
  if (n >= 70) return 'high';
  if (n >= 50) return 'moderate';
  return 'low';
}

function parsePricePosition(pos: string | undefined): { rank: number; total: number } {
  if (!pos) return { rank: 0, total: 0 };
  const match = pos.match(/#?\s*(\d+)\s*\/\s*(\d+)/);
  if (match) return { rank: parseInt(match[1], 10), total: parseInt(match[2], 10) };
  return { rank: 0, total: 0 };
}

function mapProgressStep(step: ProgressStep): AnalysisStep {
  return {
    id: step.id,
    name: step.label,
    status: step.status as AnalysisStep['status'],
    message: undefined,
  };
}

export function mapJobToAnalysis(job: JobStatusResponse): AnalysisResult {
  const summary = job.result_summary ?? {};
  const evidence = job.evidence_found ?? {};
  const quality = job.analysis_quality ?? {};
  const steps = (job.progress_steps ?? []).map(mapProgressStep);

  const yourPriceNum = parseFloat(String(evidence.own_price ?? '').replace(/[^\d.-]/g, '')) || 0;
  const marketAvgNum = parseFloat(String(evidence.compset_avg ?? '').replace(/[^\d.-]/g, '')) || 0;
  const pricePosition = parsePricePosition(evidence.price_position);
  const demandIndex = parseFloat(String(evidence.demand_score ?? 0)) || 0;
  const reputationNum = parseFloat(String(evidence.gri ?? '').replace(/[^\d.-]/g, '')) || 0;

  const compSet: Competitor[] = (evidence.top_3_competitors ?? [])
    .filter((n): n is string => typeof n === 'string' && n !== 'No encontrados')
    .map((name, i) => ({ id: `c${i + 1}`, name: safeStr(name), type: 'primary' as const }));

  const execSummary = safeStr(summary.executive_summary);
  const actionBullets = execSummary && execSummary !== NA
    ? execSummary.split(/\n/).filter(Boolean).slice(0, 5)
    : [NA];

  const qualityLabel = (quality.label === 'excellent' || quality.label === 'good' || quality.label === 'degraded' || quality.label === 'poor')
    ? quality.label
    : 'good';

  return {
    hotelId: job.job_id,
    recommendation: recommendationFromAction(summary.consolidated_action),
    confidence: summary.confidence_pct ?? 0,
    summary: execSummary,
    yourPrice: yourPriceNum,
    marketAverage: marketAvgNum,
    pricePosition: pricePosition.total ? pricePosition : { rank: 0, total: 0 },
    demandIndex,
    demandLevel: demandLevelFromScore(evidence.demand_score ?? demandIndex),
    reputation: reputationNum,
    visibility: visibilityFromString(evidence.visibility),
    marketContext: execSummary,
    events: [],
    parityStatus: parityStatusFromString(evidence.parity_status),
    channelsChecked: ['Booking.com', 'Expedia', 'Hotels.com', 'Google Hotels', 'Official Website'],
    parityMessage: safeStr(evidence.parity_status),
    compSet: compSet.length ? compSet : [{ id: 'c0', name: NA, type: 'primary' }],
    actionSummary: execSummary,
    actionBullets,
    qualityLabel,
    fallbackCount: quality.fallback_count ?? 0,
    qualityNote: safeStr(quality.summary),
    lastAnalysisRun: summary.analysis_date ? new Date(summary.analysis_date).toLocaleString() : 'Just now',
    progress: steps.length === 9 ? steps : [
      { id: 1, name: 'Identifying hotel', status: 'done' as const },
      { id: 2, name: 'Detecting comparable hotels', status: 'done' as const },
      { id: 3, name: 'Checking prices and availability', status: 'done' as const },
      { id: 4, name: 'Analyzing demand', status: 'done' as const },
      { id: 5, name: 'Analyzing reputation', status: 'done' as const },
      { id: 6, name: 'Reviewing distribution and parity', status: 'done' as const },
      { id: 7, name: 'Calculating strategy and opportunities', status: 'done' as const },
      { id: 8, name: 'Prioritizing actions and scenarios', status: 'done' as const },
      { id: 9, name: 'Generating report', status: 'done' as const },
    ],
  };
}

/** Pasos por defecto cuando aún no hay job o está arrancando (idle/running sin steps). */
export function getEmptyProgressSteps(): AnalysisStep[] {
  return [
    { id: 1, name: 'Identifying hotel', status: 'pending' },
    { id: 2, name: 'Detecting comparable hotels', status: 'pending' },
    { id: 3, name: 'Checking prices and availability', status: 'pending' },
    { id: 4, name: 'Analyzing demand', status: 'pending' },
    { id: 5, name: 'Analyzing reputation', status: 'pending' },
    { id: 6, name: 'Reviewing distribution and parity', status: 'pending' },
    { id: 7, name: 'Calculating strategy and opportunities', status: 'pending' },
    { id: 8, name: 'Prioritizing actions and scenarios', status: 'pending' },
    { id: 9, name: 'Generating report', status: 'pending' },
  ];
}
