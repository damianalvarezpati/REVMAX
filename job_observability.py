"""
RevMax — Observabilidad del job engine.
Snapshot de runtime vs persistencia para diagnóstico.
"""

from typing import Any, Callable, Dict, List

import job_state
from job_schema import ACTIVE_STATUSES


def get_runtime_snapshot(
    base_dir: str,
    get_active_job_ids_fn: Callable[[], List[str]],
    is_running_fn: Callable[[str], bool],
    limit_recent: int = 200,
) -> dict:
    """
    Devuelve un snapshot útil para diagnóstico:
    - job_ids activos en runtime (con task vivo)
    - por cada uno: si el task está done/cancelled (ya no vivo)
    - mismatch: activos en persistencia sin task vivo (orphaned), y en runtime sin job activo en persistencia
    - conteos por estado (persistencia)

    get_active_job_ids_fn: sin argumentos, devuelve lista de job_id con task vivo (ej: job_runtime.get_active_job_ids)
    is_running_fn: job_id -> bool (ej: job_runtime.is_running)
    """
    active_in_runtime: List[str] = list(get_active_job_ids_fn())
    recent = job_state.list_recent_jobs(base_dir, limit=limit_recent)
    by_status: Dict[str, int] = {}
    active_in_state: List[Dict[str, Any]] = []
    for j in recent:
        s = j.get("status") or "unknown"
        by_status[s] = by_status.get(s, 0) + 1
        if s in ACTIVE_STATUSES:
            active_in_state.append({"job_id": j.get("job_id"), "hotel_name": j.get("hotel_name"), "status": s})

    # Orphaned: activos en persistencia pero no vivos en runtime
    orphaned = [a for a in active_in_state if not is_running_fn(a["job_id"])]
    # En runtime pero sin job en persistencia o job no activo
    runtime_ids_set = set(active_in_runtime)
    state_active_ids = {a["job_id"] for a in active_in_state}
    in_runtime_not_active_state: List[str] = []
    for jid in active_in_runtime:
        job = job_state.get_job(base_dir, jid)
        if job is None:
            in_runtime_not_active_state.append(jid)
        elif job.get("status") not in ACTIVE_STATUSES:
            in_runtime_not_active_state.append(jid)

    return {
        "active_job_ids": active_in_runtime,
        "active_count_runtime": len(active_in_runtime),
        "by_status": by_status,
        "orphaned": [{"job_id": o["job_id"], "hotel_name": o["hotel_name"], "status": o["status"]} for o in orphaned],
        "in_runtime_not_active_state": in_runtime_not_active_state,
        "mismatch_summary": {
            "orphaned_count": len(orphaned),
            "runtime_without_active_state_count": len(in_runtime_not_active_state),
        },
    }
