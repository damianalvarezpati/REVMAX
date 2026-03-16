"""
RevMax — Artefactos de debug por corrida (data/debug_runs/<job_id>/).
Escribe outputs por fase, briefing, report prompt/raw/normalized, summary.json.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional


def get_debug_dir(base_dir: str, job_id: str) -> str:
    """Ruta a data/debug_runs/<job_id>/."""
    path = os.path.join(base_dir, "data", "debug_runs", job_id)
    return path


def ensure_debug_dir(debug_dir: str) -> None:
    os.makedirs(debug_dir, exist_ok=True)


def save_debug_artifact(debug_dir: str, name: str, data: Any, as_json: bool = True) -> None:
    """Guarda un artefacto en debug_dir. name sin extensión; se añade .json o .txt."""
    if not debug_dir:
        return
    ensure_debug_dir(debug_dir)
    ext = ".json" if as_json else ".txt"
    path = os.path.join(debug_dir, name + ext)
    try:
        with open(path, "w", encoding="utf-8") as f:
            if as_json:
                json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                f.write(data if isinstance(data, str) else str(data))
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"[debug_runs] failed to save {name}: {e}", flush=True)


def write_summary(
    debug_dir: str,
    *,
    job_id: str,
    hotel_name: str,
    status: str,
    failed_phase: Optional[str] = None,
    error_message: Optional[str] = None,
    exception_type: Optional[str] = None,
    discovery_duration: Optional[float] = None,
    compset_duration: Optional[float] = None,
    pricing_duration: Optional[float] = None,
    demand_duration: Optional[float] = None,
    reputation_duration: Optional[float] = None,
    distribution_duration: Optional[float] = None,
    consolidate_duration: Optional[float] = None,
    report_duration: Optional[float] = None,
    render_duration: Optional[float] = None,
    total_duration: Optional[float] = None,
    fallback_count: Optional[int] = None,
    completed_at: Optional[str] = None,
) -> None:
    """Escribe summary.json con timings y estado."""
    if not debug_dir:
        return
    ensure_debug_dir(debug_dir)
    summary = {
        "job_id": job_id,
        "hotel_name": hotel_name,
        "status": status,
        "failed_phase": failed_phase,
        "error_message": error_message,
        "exception_type": exception_type,
        "discovery_duration": discovery_duration,
        "compset_duration": compset_duration,
        "pricing_duration": pricing_duration,
        "demand_duration": demand_duration,
        "reputation_duration": reputation_duration,
        "distribution_duration": distribution_duration,
        "consolidate_duration": consolidate_duration,
        "report_duration": report_duration,
        "render_duration": render_duration,
        "total_duration": total_duration,
        "fallback_count": fallback_count,
        "completed_at": completed_at or datetime.utcnow().isoformat() + "Z",
    }
    path = os.path.join(debug_dir, "summary.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"[debug_runs] failed to write summary: {e}", flush=True)
