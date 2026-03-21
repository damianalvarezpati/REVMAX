/**
 * Cliente API para el backend RevMax.
 * Analysis usa POST /api/run-analysis y GET /api/job-status/{job_id}.
 */

import { getApiUrl } from './config';

export type JobStatus =
  | 'pending'
  | 'running'
  | 'rendering'
  | 'persisting'
  | 'notifying'
  | 'completed'
  | 'failed'
  | 'stalled'
  | 'cancelled';

export interface ProgressStep {
  id: number;
  label: string;
  status: 'pending' | 'active' | 'done' | 'error' | 'warning';
}

export interface ResultSummary {
  consolidated_action?: string;
  confidence_pct?: number | null;
  executive_summary?: string;
  analysis_date?: string;
  decision_comparison?: DecisionComparison;
}

export interface DecisionComparison {
  legacy_decision?: 'raise' | 'hold' | 'lower' | 'unknown';
  deterministic_pro_decision?: 'raise' | 'hold' | 'lower' | 'unknown';
  match?: boolean;
  difference_type?: string;
  comment?: string;
  legacy_reasons?: string[];
  pro_reasons?: string[];
  constraints_applied?: string[];
  missing_data?: string[];
}

export interface EvidenceFound {
  hotel_detected?: string;
  city?: string;
  own_price?: string;
  compset_avg?: string;
  price_position?: string;
  gri?: string;
  visibility?: string;
  parity_status?: string;
  demand_score?: string;
  top_3_competitors?: string[];
  is_degraded?: boolean;
}

export interface AnalysisQuality {
  label?: string;
  score?: number;
  fallback_count?: number;
  agents_ok?: number;
  agents_fallback?: number;
  agents_total?: number;
  summary?: string;
}

export interface JobStatusResponse {
  job_id: string;
  hotel_name: string;
  city?: string;
  status: JobStatus;
  stage?: string;
  progress_pct?: number;
  error_message?: string | null;
  progress_steps: ProgressStep[];
  result_summary?: ResultSummary | null;
  evidence_found?: EvidenceFound | null;
  analysis_quality?: AnalysisQuality | null;
  analysis_timing?: Record<string, number> | null;
}

export interface RunAnalysisResponse {
  ok: boolean;
  job_id?: string;
  message?: string;
  error?: string;
  active_job_id?: string;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = getApiUrl(path);
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error((data as { error?: string }).error || (data as { message?: string }).message || `HTTP ${res.status}`);
  }
  return data as T;
}

export async function runAnalysis(params: {
  hotel_name: string;
  city?: string;
  hotel_id?: number;
  send_email?: boolean;
  fast_demo?: boolean;
}): Promise<RunAnalysisResponse> {
  return request<RunAnalysisResponse>('/api/run-analysis', {
    method: 'POST',
    body: JSON.stringify({
      hotel_name: params.hotel_name,
      city: params.city ?? '',
      hotel_id: params.hotel_id ?? 1,
      send_email: params.send_email ?? false,
      fast_demo: params.fast_demo ?? false,
    }),
  });
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  return request<JobStatusResponse>(`/api/job-status/${encodeURIComponent(jobId)}`);
}

/** Equilibrio activo de conocimiento (knowledge_balancing_engine) */
export interface KnowledgeBalanceBlock {
  current_area_score?: number;
  target_area_score?: number;
  knowledge_gap_score?: number;
  growth_priority?: number;
  mode?: 'growth' | 'monitor' | 'maintenance';
  growth_mode?: boolean;
  maintenance_mode?: boolean;
  recommended_effort_share?: number;
  human_validation_priority?: number;
  recommended_actions?: string[];
  why_this_area_needs_attention?: string;
  suggested_data_actions?: string[];
  suggested_human_validation_actions?: string[];
}

/** Dojo — Knowledge Inputs (madurez por área) */
export interface KnowledgeInputArea {
  area_key: string;
  area_name: string;
  datasets_count: number;
  real_cases_count: number;
  synthetic_cases_count: number;
  validated_cases_count: number;
  rules_supported_count: number;
  hypotheses_pending_count: number;
  coverage_score: number;
  quality_score: number;
  validation_score: number;
  model_readiness_score: number;
  area_score: number;
  status_label: string;
  missing_gaps: string[];
  suggested_actions: string[];
  accepted_quality_bonus_points?: number;
  knowledge_balance?: KnowledgeBalanceBlock;
  area_blocked_by_validation?: boolean;
  validation_debt_score?: number;
  pending_validation_tasks_count?: number;
  pending_hypothesis_reviews_count?: number;
  validation_debt_penalty?: number;
}

export interface ValidationInboxTask {
  task_id: string;
  task_type?: string;
  area_key?: string;
  priority?: number;
  reason?: string;
  status?: string;
  required_for_area_progress?: boolean;
  linked_case_id?: string | null;
  linked_rule_id?: string | null;
  linked_hypothesis_id?: string | null;
  dismiss_reason?: string;
  closed_by?: string;
  closed_at?: string;
  closure_source?: string;
  validation_debt_impact?: { before?: number; after?: number };
}

export interface DojoValidationInboxPayload {
  global_metrics?: {
    dojo_inbox_count?: number;
    overdue_reviews_count?: number;
    areas_blocked_count?: number;
    pending_by_type?: Record<string, number>;
  };
  updated_at?: string | null;
  pending_tasks_preview?: ValidationInboxTask[];
}

/** Respuesta completa GET /api/dojo/validation-inbox */
export interface ValidationInboxFullResponse {
  inbox: {
    version?: number;
    updated_at?: string | null;
    tasks?: ValidationInboxTask[];
  };
  global_metrics: {
    dojo_inbox_count?: number;
    overdue_reviews_count?: number;
    areas_blocked_count?: number;
    pending_by_type?: Record<string, number>;
    pending_validation_tasks?: number;
    pending_hypothesis_reviews?: number;
    pending_rule_reviews?: number;
    pending_compset_reviews?: number;
    pending_decision_reviews?: number;
    pending_other?: number;
  };
  per_area_metrics: Record<string, Record<string, unknown>>;
  blocked_areas?: { area_key: string; validation_debt_score?: number; required_pending_count?: number }[];
}

/** Bloque funnel (run + lifetime) escrito por knowledge_refresh */
export interface RefreshFunnelBlock {
  this_run?: {
    observed_count?: number;
    accepted_count?: number;
    dojo_candidates_generated?: number;
    dojo_candidates_validated?: number;
    runs_with_meaningful_output?: number;
    runs_with_delta?: number;
    area_score_changes_count?: number;
    acceptance_rate?: number | null;
  };
  lifetime?: Record<string, number | string | null | undefined>;
}

/** Último knowledge refresh (GET knowledge-inputs lo incluye) */
export interface KnowledgeRefreshSummary {
  run_id?: string;
  mode?: string;
  finished_at?: string;
  areas_reviewed?: string[];
  observed_count?: number;
  accepted_count?: number;
  dojo_candidates_created?: number;
  score_deltas_by_area?: Record<
    string,
    { before?: number; after?: number; delta_area_score?: number | null }
  >;
  hypothesis_events_count?: number;
  funnel?: RefreshFunnelBlock | null;
  funnel_metrics?: Record<string, number | string | null | undefined>;
  funnel_lifetime?: Record<string, number | string | null | undefined>;
  funnel_file_last_updated?: string;
}

export interface KnowledgeInputsResponse {
  generated_at: string;
  areas: KnowledgeInputArea[];
  meta?: Record<string, unknown>;
  scoring_notes?: Record<string, string>;
  knowledge_balance_summary?: {
    areas_in_growth?: string[];
    areas_in_maintenance?: string[];
    total_effort_share_check?: number;
    balancing_config_path?: string;
  };
  knowledge_refresh?: KnowledgeRefreshSummary | null;
  dojo_validation_inbox?: DojoValidationInboxPayload;
  error?: string;
}

export async function getKnowledgeInputs(): Promise<KnowledgeInputsResponse> {
  return request<KnowledgeInputsResponse>('/api/dojo/knowledge-inputs');
}

export async function getValidationInbox(): Promise<ValidationInboxFullResponse> {
  return request<ValidationInboxFullResponse>('/api/dojo/validation-inbox');
}

export async function updateValidationInboxTask(
  taskId: string,
  body: {
    status: 'done' | 'dismissed' | 'pending';
    assigned_to?: string;
    dismiss_reason?: string;
    closed_by?: string;
    closure_source?: string;
  },
): Promise<{ ok?: boolean; task_id?: string; status?: string; error?: string }> {
  return request(`/api/dojo/validation-inbox/tasks/${encodeURIComponent(taskId)}`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/** Abre JSON del caso QA en nueva pestaña (GET /api/dojo/qa-case-preview). */
export function getDojoQaCasePreviewUrl(casePath: string): string {
  return getApiUrl(`/api/dojo/qa-case-preview?path=${encodeURIComponent(casePath)}`);
}

export function getDojoRuleByIdUrl(ruleId: string): string {
  return getApiUrl(`/api/dojo/rule-by-id?rule_id=${encodeURIComponent(ruleId)}`);
}
