"""
RevMax — Detección de jobs colgados (stalled).
Marca jobs que llevan demasiado tiempo en estado activo sin actualizar updated_at.

Reconciliación runtime vs persistencia:
- Si is_alive(job_id) es True (task vivo en runtime), el job NUNCA se marca stalled.
- Solo se marca stalled cuando: estado activo AND runtime no tiene task viva AND idle > max_idle_seconds.
"""

from datetime import datetime, timezone
from typing import Callable, List, Optional, Tuple

from job_schema import ACTIVE_STATUSES
import job_state


def _parse_iso(s: str) -> datetime:
    """Convierte ISO 8601 con Z a datetime UTC (timezone-aware)."""
    if not s:
        return datetime.min.replace(tzinfo=timezone.utc)
    s = (s or "").strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def mark_stale_jobs(
    base_dir: str,
    max_idle_seconds: float,
    stalled_message: str = "Job marcado como colgado: sin actualización en el tiempo límite.",
    *,
    is_alive: Optional[Callable[[str], bool]] = None,
    dry_run: bool = False,
) -> dict:
    """
    Busca jobs en estado activo cuyo updated_at sea más antiguo que max_idle_seconds
    y los marca como stalled, EXCEPTO si is_alive(job_id) es True (task vivo en runtime).

    Lógica:
    1) job.status en ACTIVE_STATUSES
    2) si is_alive(job_id) True -> NO marcar stalled, incrementar alive_in_runtime
    Solo marcar stalled cuando: estado activo AND runtime no tiene task viva AND idle > max_idle_seconds.

    Devuelve: reviewed, active_count, alive_in_runtime, marked_stalled (int), marked_stalled_ids (list), ignored.
    """
    now = datetime.now(timezone.utc)
    recent = job_state.list_recent_jobs(base_dir, limit=500)
    reviewed = len(recent)
    active_jobs: List[dict] = []
    for j in recent:
        if j.get("status") in ACTIVE_STATUSES:
            active_jobs.append(j)
    active_count = len(active_jobs)
    alive_in_runtime = 0
    marked: List[Tuple[str, str]] = []
    for j in active_jobs:
        job_id = j.get("job_id")
        if is_alive and is_alive(job_id):
            alive_in_runtime += 1
            continue
        updated_raw = j.get("updated_at")
        try:
            updated = _parse_iso(updated_raw) if updated_raw else now
        except Exception:
            updated = now
        if (now - updated).total_seconds() < max_idle_seconds:
            continue
        hotel_name = (j.get("hotel_name") or "").strip()
        if not dry_run:
            completed_at = now.isoformat().replace("+00:00", "Z")
            job_state.update_job(
                base_dir,
                job_id,
                status="stalled",
                stage="error",
                error_message=stalled_message,
                completed_at=completed_at,
            )
        marked.append((job_id, hotel_name))
    ignored = alive_in_runtime
    return {
        "reviewed": reviewed,
        "active_count": active_count,
        "alive_in_runtime": alive_in_runtime,
        "marked_stalled": len(marked),
        "marked_stalled_ids": [m[0] for m in marked],
        "ignored": ignored,
        "dry_run": dry_run,
    }
