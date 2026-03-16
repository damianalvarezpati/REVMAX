'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { AnalysisHero } from '@/components/analysis/analysis-hero';
import { MarketSnapshot } from '@/components/analysis/market-snapshot';
import { MarketContext } from '@/components/analysis/market-context';
import { EventsDetected } from '@/components/analysis/events-detected';
import { DistributionParity } from '@/components/analysis/distribution-parity';
import { CompSetEditor } from '@/components/analysis/comp-set-editor';
import { RecommendedAction } from '@/components/analysis/recommended-action';
import { ConfidenceQuality } from '@/components/analysis/confidence-quality';
import { ProgressPanel } from '@/components/analysis/progress-panel';
import { SetupPanel } from '@/components/analysis/setup-panel';
import { getJobStatus, runAnalysis } from '@/lib/revmax';
import type { JobStatusResponse } from '@/lib/revmax';
import { mapJobToAnalysis, getEmptyProgressSteps } from '@/lib/analysis-from-job';
import type { AnalysisResult } from '@/lib/mock-data';
import { Building2 } from 'lucide-react';

const POLL_INTERVAL_MS = 2000;
const TERMINAL_STATUSES = ['completed', 'failed', 'stalled', 'cancelled'];

type UiStatus = 'idle' | 'running' | 'completed' | 'failed' | 'stalled' | 'degraded';

function mapJobStatusToUi(status: string, job?: JobStatusResponse): UiStatus {
  if (TERMINAL_STATUSES.includes(status)) {
    if (status === 'completed') {
      const degraded =
        job?.evidence_found?.is_degraded ||
        (job?.analysis_quality?.label &&
          job.analysis_quality.label !== 'excellent' &&
          job.analysis_quality.label !== 'good');
      return degraded ? 'degraded' : 'completed';
    }
    if (status === 'stalled') return 'stalled';
    return 'failed';
  }
  return 'running';
}

export default function AnalysisPage() {
  const [hotelName, setHotelName] = useState('');
  const [city, setCity] = useState('');
  const [fastDemo, setFastDemo] = useState(false);
  const [uiStatus, setUiStatus] = useState<UiStatus>('idle');
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<JobStatusResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const poll = useCallback(() => {
    if (!jobId) return;
    getJobStatus(jobId)
      .then((data) => {
        setJob(data);
        const status = data.status;
        if (TERMINAL_STATUSES.includes(status)) {
          stopPolling();
          setUiStatus(mapJobStatusToUi(status, data));
          if (status === 'failed' || status === 'stalled') {
            setErrorMessage(data.error_message ?? 'Error');
          }
        }
      })
      .catch(() => {
        stopPolling();
        setUiStatus('failed');
        setErrorMessage('Error al obtener estado del job');
      });
  }, [jobId, stopPolling]);

  useEffect(() => {
    if (uiStatus !== 'running' || !jobId) return;
    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => stopPolling();
  }, [uiStatus, jobId, poll, stopPolling]);

  const handleRunAnalysis = async () => {
    const name = hotelName.trim();
    if (!name) {
      setErrorMessage('Indica el nombre del hotel');
      return;
    }
    setErrorMessage(null);
    setJob(null);
    setJobId(null);
    try {
      const res = await runAnalysis({
        hotel_name: name,
        city: city.trim() || undefined,
        hotel_id: 1,
        fast_demo: fastDemo,
      });
      if (res.error && !res.job_id) {
        setErrorMessage(res.error);
        return;
      }
      if (res.active_job_id && res.error) {
        setJobId(res.active_job_id);
        setUiStatus('running');
        setErrorMessage(res.error);
        return;
      }
      const id = res.job_id;
      if (!id) {
        setErrorMessage(res.error ?? 'No job_id');
        return;
      }
      setJobId(id);
      setUiStatus('running');
    } catch (e) {
      setUiStatus('failed');
      setErrorMessage(e instanceof Error ? e.message : 'Error al lanzar análisis');
    }
  };

  const isRunning = uiStatus === 'running';
  const hasResult = uiStatus === 'completed' || uiStatus === 'degraded';
  const analysis: AnalysisResult | null = job && hasResult ? mapJobToAnalysis(job) : null;
  const progressSteps = job?.progress_steps?.length
    ? job.progress_steps.map((s) => ({ id: s.id, name: s.label, status: s.status as 'done' | 'active' | 'warning' | 'error' | 'pending' }))
    : getEmptyProgressSteps();

  return (
    <div className="flex gap-6">
      <div className="flex-1 max-w-4xl space-y-6">
        {/* Header: hotel being analyzed or prompt */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground mb-1">Analyzing</p>
            <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
              <Building2 className="h-6 w-6 text-primary" />
              {job?.hotel_name || hotelName || 'Analysis'}
            </h1>
            {(job?.city || city) && (
              <p className="text-sm text-muted-foreground mt-1">{job?.city || city}</p>
            )}
          </div>
        </div>

        {/* Hero: real result or placeholder / error */}
        {hasResult && analysis && <AnalysisHero analysis={analysis} />}
        {uiStatus === 'idle' && (
          <div className="rounded-2xl border border-dashed border-border/50 p-8 text-center text-muted-foreground">
            Enter hotel name and city, then run analysis to see the recommendation and market snapshot.
          </div>
        )}
        {isRunning && (
          <div className="rounded-2xl border border-primary/20 bg-primary/5 p-6 text-center">
            <p className="text-sm font-medium text-foreground">Analysis in progress…</p>
            <p className="text-xs text-muted-foreground mt-1">Results will appear below when complete.</p>
          </div>
        )}
        {(uiStatus === 'failed' || uiStatus === 'stalled') && job && (
          <div className="rounded-2xl border border-destructive/30 bg-destructive/5 p-6">
            <p className="text-sm font-medium text-destructive">
              {uiStatus === 'stalled' ? 'Job stalled' : 'Analysis failed'}
            </p>
            <p className="text-sm text-muted-foreground mt-1">{job.error_message ?? 'No details'}</p>
          </div>
        )}

        {/* Rest of sections: only when we have real analysis */}
        {hasResult && analysis && (
          <>
            <MarketSnapshot analysis={analysis} />
            <MarketContext context={analysis.marketContext} />
            <EventsDetected events={analysis.events} />
            <DistributionParity
              status={analysis.parityStatus}
              channels={analysis.channelsChecked}
              message={analysis.parityMessage}
            />
            <CompSetEditor compSet={analysis.compSet} />
            <RecommendedAction summary={analysis.actionSummary} bullets={analysis.actionBullets} />
            <ConfidenceQuality
              quality={analysis.qualityLabel}
              confidence={analysis.confidence}
              fallbackCount={analysis.fallbackCount}
              note={analysis.qualityNote}
            />
          </>
        )}
      </div>

      <div className="w-80 space-y-6 shrink-0">
        <SetupPanel
          hotelName={hotelName}
          city={city}
          fastDemo={fastDemo}
          onHotelNameChange={setHotelName}
          onCityChange={setCity}
          onFastDemoChange={setFastDemo}
          onRunAnalysis={handleRunAnalysis}
          isRunning={isRunning}
          errorMessage={errorMessage}
          currentJobHotel={isRunning ? job?.hotel_name : null}
        />
        <ProgressPanel steps={progressSteps} isRunning={isRunning} />
      </div>
    </div>
  );
}
