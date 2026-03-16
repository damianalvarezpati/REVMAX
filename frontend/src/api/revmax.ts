/**
 * Cliente API para el backend RevMax.
 * Conecta la pantalla Analysis con POST /api/run-analysis y GET /api/job-status/{job_id}.
 */

import { getApiUrl } from '../config'

export type JobStatus =
  | 'pending'
  | 'running'
  | 'rendering'
  | 'persisting'
  | 'notifying'
  | 'completed'
  | 'failed'
  | 'stalled'
  | 'cancelled'

export interface ProgressStep {
  id: number
  label: string
  status: 'pending' | 'active' | 'done' | 'error' | 'warning'
}

export interface ResultSummary {
  consolidated_action?: string
  confidence_pct?: number | null
  executive_summary?: string
  analysis_date?: string
}

export interface EvidenceFound {
  hotel_detected?: string
  city?: string
  own_price?: string
  compset_avg?: string
  price_position?: string
  gri?: string
  visibility?: string
  parity_status?: string
  demand_score?: string
  top_3_competitors?: string[]
  is_degraded?: boolean
}

export interface AnalysisQuality {
  label?: string
  score?: number
  fallback_count?: number
  agents_ok?: number
  agents_fallback?: number
  agents_total?: number
  summary?: string
}

export interface JobStatusResponse {
  job_id: string
  hotel_name: string
  city?: string
  status: JobStatus
  stage?: string
  progress_pct?: number
  error_message?: string | null
  progress_steps: ProgressStep[]
  result_summary?: ResultSummary | null
  evidence_found?: EvidenceFound | null
  analysis_quality?: AnalysisQuality | null
  analysis_timing?: Record<string, number> | null
}

export interface RunAnalysisResponse {
  ok: boolean
  job_id: string
  message?: string
  error?: string
  active_job_id?: string
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = getApiUrl(path)
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(data?.error || data?.message || `HTTP ${res.status}`)
  }
  return data as T
}

/**
 * Lanza un análisis. Devuelve job_id para hacer polling.
 */
export async function runAnalysis(params: {
  hotel_name: string
  city?: string
  hotel_id?: number
  send_email?: boolean
  fast_demo?: boolean
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
  })
}

/**
 * Obtiene el estado de un job (progreso, resultado, evidencias).
 */
export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  return request<JobStatusResponse>(`/api/job-status/${encodeURIComponent(jobId)}`)
}
