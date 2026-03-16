/**
 * Pantalla Analysis conectada al backend real RevMax.
 * - POST /api/run-analysis para lanzar
 * - GET /api/job-status/{job_id} para progreso y resultado
 * Estados UI: idle | running | completed | failed | stalled | degraded
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  getJobStatus,
  runAnalysis,
  type JobStatusResponse,
  type ProgressStep,
  type ResultSummary,
  type EvidenceFound,
  type AnalysisQuality,
} from '../api/revmax'

type UiStatus = 'idle' | 'running' | 'completed' | 'failed' | 'stalled' | 'degraded'

const POLL_INTERVAL_MS = 2000
const TERMINAL_STATUSES = ['completed', 'failed', 'stalled', 'cancelled']

function safeStr(val: unknown): string {
  if (val == null || val === '') return 'No encontrado'
  return String(val)
}

function mapJobStatusToUi(status: string, job?: JobStatusResponse): UiStatus {
  if (TERMINAL_STATUSES.includes(status)) {
    if (status === 'completed') {
      const degraded =
        job?.evidence_found?.is_degraded ||
        (job?.analysis_quality?.label && job.analysis_quality.label !== 'excellent' && job.analysis_quality.label !== 'good')
      return degraded ? 'degraded' : 'completed'
    }
    if (status === 'stalled') return 'stalled'
    return 'failed'
  }
  return 'running'
}

export default function Analysis() {
  const [hotelName, setHotelName] = useState('')
  const [city, setCity] = useState('')
  const [fastDemo, setFastDemo] = useState(false)
  const [uiStatus, setUiStatus] = useState<UiStatus>('idle')
  const [jobId, setJobId] = useState<string | null>(null)
  const [job, setJob] = useState<JobStatusResponse | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const poll = useCallback(() => {
    if (!jobId) return
    getJobStatus(jobId)
      .then((data) => {
        setJob(data)
        const status = data.status
        if (TERMINAL_STATUSES.includes(status)) {
          stopPolling()
          setUiStatus(mapJobStatusToUi(status, data))
          if (status === 'failed' || status === 'stalled') {
            setErrorMessage(safeStr(data.error_message))
          }
        }
      })
      .catch(() => {
        stopPolling()
        setUiStatus('failed')
        setErrorMessage('Error al obtener estado del job')
      })
  }, [jobId, stopPolling])

  useEffect(() => {
    if (uiStatus !== 'running' || !jobId) return
    poll()
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS)
    return () => stopPolling()
  }, [uiStatus, jobId, poll, stopPolling])

  const handleRunAnalysis = async () => {
    const name = hotelName.trim()
    if (!name) {
      setErrorMessage('Indica el nombre del hotel')
      return
    }
    setErrorMessage(null)
    setJob(null)
    setJobId(null)
    try {
      const res = await runAnalysis({
        hotel_name: name,
        city: city.trim() || undefined,
        hotel_id: 1,
        fast_demo: fastDemo,
      })
      if (res.error && !res.job_id) {
        setErrorMessage(res.error)
        return
      }
      if (res.active_job_id && res.error) {
        setJobId(res.active_job_id)
        setUiStatus('running')
        setErrorMessage(res.error)
        return
      }
      setJobId(res.job_id)
      setUiStatus('running')
    } catch (e) {
      setUiStatus('failed')
      setErrorMessage(e instanceof Error ? e.message : 'Error al lanzar análisis')
    }
  }

  const progressSteps: ProgressStep[] = job?.progress_steps ?? []
  const resultSummary: ResultSummary | undefined = job?.result_summary ?? undefined
  const evidence: EvidenceFound | undefined = job?.evidence_found ?? undefined
  const quality: AnalysisQuality | undefined = job?.analysis_quality ?? undefined

  return (
    <div>
      <h1 style={{ marginBottom: 24, fontSize: 24, fontWeight: 700 }}>Analysis</h1>

      {/* Setup panel */}
      <section className="card setup-panel" id="setup-panel">
        <div className="card-title">Setup</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center', marginBottom: 16 }}>
          <input
            className="form-input"
            placeholder="Nombre del hotel"
            value={hotelName}
            onChange={(e) => setHotelName(e.target.value)}
            disabled={uiStatus === 'running'}
          />
          <input
            className="form-input"
            placeholder="Ciudad (opcional)"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            disabled={uiStatus === 'running'}
          />
          <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <input
              type="checkbox"
              checked={fastDemo}
              onChange={(e) => setFastDemo(e.target.checked)}
              disabled={uiStatus === 'running'}
            />
            Demo rápido
          </label>
          <button
            className="btn btn-primary"
            onClick={handleRunAnalysis}
            disabled={uiStatus === 'running'}
          >
            {uiStatus === 'running' ? 'Analizando…' : 'Run analysis'}
          </button>
        </div>
        {errorMessage && (
          <div style={{ color: 'var(--error)', fontSize: 13 }}>{errorMessage}</div>
        )}
        {jobId && uiStatus === 'running' && (
          <div style={{ fontSize: 12, color: 'var(--secondary)' }}>Job: {jobId}</div>
        )}
      </section>

      {/* Progress panel */}
      <section className="card progress-panel" id="progress-panel">
        <div className="card-title">Progress</div>
        {progressSteps.length === 0 && uiStatus === 'idle' && (
          <p style={{ color: 'var(--secondary)' }}>Lanza un análisis para ver el progreso.</p>
        )}
        {progressSteps.length > 0 && (
          <div>
            {progressSteps.map((step) => (
              <div
                key={step.id}
                className={`progress-step ${step.status}`}
              >
                <span className="dot" />
                <span>{safeStr(step.label)}</span>
                <span style={{ marginLeft: 'auto', fontSize: 11 }}>{step.status}</span>
              </div>
            ))}
          </div>
        )}
        {job?.progress_pct != null && uiStatus === 'running' && (
          <div style={{ marginTop: 12, fontSize: 13 }}>{job.progress_pct}%</div>
        )}
      </section>

      {/* Analysis Hero */}
      <section className="card analysis-hero" id="analysis-hero">
        <div className="card-title">Hero decision</div>
        {(uiStatus === 'idle' || uiStatus === 'running') && !resultSummary && (
          <p style={{ color: 'var(--secondary)' }}>El resultado aparecerá aquí al completar el análisis.</p>
        )}
        {(uiStatus === 'completed' || uiStatus === 'degraded') && resultSummary && (
          <>
            <div style={{ marginBottom: 8 }}>
              <span className={`badge badge-${(resultSummary.consolidated_action ?? '').toLowerCase() === 'raise' ? 'success' : (resultSummary.consolidated_action ?? '').toLowerCase() === 'lower' ? 'warning' : 'info'}`}>
                {safeStr(resultSummary.consolidated_action).toUpperCase()}
              </span>
            </div>
            <div className="confidence-line" style={{ marginBottom: 16 }}>
              Confidence {resultSummary.confidence_pct != null ? resultSummary.confidence_pct : '—'}%
            </div>
            <p style={{ fontSize: 15, lineHeight: 1.6 }}>{safeStr(resultSummary.executive_summary)}</p>
          </>
        )}
        {(uiStatus === 'failed' || uiStatus === 'stalled') && job && (
          <p style={{ color: 'var(--error)' }}>{safeStr(job.error_message)}</p>
        )}
      </section>

      {/* Market snapshot */}
      <section className="card" id="market-snapshot">
        <div className="card-title">Market snapshot</div>
        {!evidence && uiStatus !== 'running' && <p style={{ color: 'var(--secondary)' }}>No encontrado</p>}
        {evidence && (
          <ul style={{ listStyle: 'none' }}>
            <li>Hotel: {safeStr(evidence.hotel_detected)}</li>
            <li>Ciudad: {safeStr(evidence.city)}</li>
            <li>Precio propio: {safeStr(evidence.own_price)}</li>
            <li>Compset avg: {safeStr(evidence.compset_avg)}</li>
            <li>Posición: {safeStr(evidence.price_position)}</li>
          </ul>
        )}
      </section>

      {/* Market context */}
      <section className="card" id="market-context">
        <div className="card-title">Market context</div>
        {evidence && (
          <p style={{ lineHeight: 1.6 }}>
            {resultSummary?.executive_summary ? safeStr(resultSummary.executive_summary) : 'Se detecta demanda estable en la zona. Revisa el informe para el contexto completo.'}
          </p>
        )}
        {!evidence && uiStatus !== 'running' && <p style={{ color: 'var(--secondary)' }}>No encontrado</p>}
      </section>

      {/* Events */}
      <section className="card" id="events-detected">
        <div className="card-title">Events detected</div>
        {evidence && (
          <ul style={{ listStyle: 'none' }}>
            <li>Demand score: {safeStr(evidence.demand_score)}</li>
            <li>GRI: {safeStr(evidence.gri)}</li>
            <li>Visibility: {safeStr(evidence.visibility)}</li>
          </ul>
        )}
        {!evidence && uiStatus !== 'running' && <p style={{ color: 'var(--secondary)' }}>No encontrado</p>}
      </section>

      {/* Distribution & parity */}
      <section className="card" id="distribution-parity">
        <div className="card-title">Distribution & parity</div>
        {evidence && (
          <p>Parity status: {safeStr(evidence.parity_status)}</p>
        )}
        {!evidence && uiStatus !== 'running' && <p style={{ color: 'var(--secondary)' }}>No encontrado</p>}
      </section>

      {/* Comp set */}
      <section className="card" id="comp-set-editor">
        <div className="card-title">Comp set</div>
        {evidence?.top_3_competitors && evidence.top_3_competitors.length > 0 ? (
          <ul className="compset-list" style={{ listStyle: 'none' }}>
            {evidence.top_3_competitors.map((name, i) => (
              <li key={i}>{safeStr(name)}</li>
            ))}
          </ul>
        ) : (
          <p style={{ color: 'var(--secondary)' }}>{uiStatus === 'idle' || uiStatus === 'running' ? '—' : 'No encontrados'}</p>
        )}
      </section>

      {/* Recommended action */}
      <section className="card" id="recommended-action">
        <div className="card-title">Recommended action</div>
        {resultSummary?.executive_summary ? (
          <p className="recommended-action-text" style={{ fontSize: 15, lineHeight: 1.6 }}>
            {safeStr(resultSummary.executive_summary)}
          </p>
        ) : (
          <p style={{ color: 'var(--secondary)' }}>{uiStatus === 'idle' || uiStatus === 'running' ? '—' : 'No encontrado'}</p>
        )}
      </section>

      {/* Confidence & quality */}
      <section className="card" id="confidence-quality">
        <div className="card-title">Confidence & data quality</div>
        {quality && (
          <>
            <p>Label: {safeStr(quality.label)}</p>
            <p>Score: {quality.score != null ? quality.score : '—'}</p>
            <p>Confidence: {resultSummary?.confidence_pct != null ? resultSummary.confidence_pct : '—'}%</p>
            <p style={{ marginTop: 8 }}>{safeStr(quality.summary)}</p>
          </>
        )}
        {!quality && uiStatus !== 'running' && <p style={{ color: 'var(--secondary)' }}>No encontrado</p>}
      </section>
    </div>
  )
}
