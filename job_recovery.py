"""
RevMax — Startup / crash recovery.
Sanea jobs que quedaron en estado activo tras una caída del proceso (sin task viva en runtime).
"""

from datetime import datetime, timezone
from typing import Callable, List, Optional, Tuple

from job_schema import ACTIVE_STATUSES
import job_state

# Política por defecto: marcar como stalled (recuperable conceptualmente; el usuario puede relanzar)
DEFAULT_RECOVERY_MESSAGE = "Proceso reiniciado: job activo sin task viva (crash recovery)."


def run_startup_recovery(
    base_dir: str,
    is_alive: Callable[[str], bool],
    *,
    policy: str = "stalled",
    message: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """
    Detecta jobs en estado activo (persistencia) que no tienen task viva en runtime (orphaned).
    Aplica la política indicada a cada uno.

    is_alive: función job_id -> bool (ej: job_runtime.is_running).
    policy: "stalled" | "failed"
      - "stalled": marca status=stalled, stage=error, completed_at=now, error_message=...
      - "failed": marca status=failed, stage=error, completed_at=now, error_message=...
    message: mensaje para error_message; si no se pasa, se usa DEFAULT_RECOVERY_MESSAGE.
    dry_run: si True, no escribe; solo devuelve la lista de jobs que se sanearían.

    Devuelve:
      orphaned: [(job_id, hotel_name, status_aplicado)]
      dry_run: bool
    """
    msg = message or DEFAULT_RECOVERY_MESSAGE
    if policy not in ("stalled", "failed"):
        raise ValueError(f"policy must be 'stalled' or 'failed', got {policy!r}")
    recent = job_state.list_recent_jobs(base_dir, limit=500)
    orphaned: List[Tuple[str, str, str]] = []
    for j in recent:
        if j.get("status") not in ACTIVE_STATUSES:
            continue
        job_id = j.get("job_id")
        if is_alive(job_id):
            continue
        hotel_name = (j.get("hotel_name") or "").strip()
        if not dry_run:
            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            job_state.update_job(
                base_dir,
                job_id,
                status=policy,
                stage="error",
                error_message=msg,
                completed_at=now_iso,
            )
        orphaned.append((job_id, hotel_name, policy))
    return {"orphaned": orphaned, "dry_run": dry_run}
