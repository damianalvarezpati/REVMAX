"""
RevMax — Capa de persistencia de estado de jobs de análisis.
Cada job se guarda en data/jobs/<job_id>.json con escritura atómica.
Validación vía job_schema: status, stage, progress_pct; claves desconocidas → ValueError.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from job_schema import (
    ALLOWED_STATUSES,
    ALLOWED_STAGES,
    ACTIVE_STATUSES,
    NULLABLE_UPDATE_KEYS,
    reject_unknown_update_keys,
    validate_progress_pct,
    validate_stage,
    validate_status,
)

JOB_KNOWN_KEYS = frozenset({
    "job_id", "hotel_name", "city", "hotel_id", "status", "stage", "progress_pct",
    "created_at", "started_at", "updated_at", "completed_at",
    "error_message", "warning_message", "result_html_path", "preview_html_path", "fast_demo",
})


def _jobs_dir(base_dir: str) -> str:
    return os.path.join(base_dir, "data", "jobs")


def _job_path(base_dir: str, job_id: str) -> str:
    return os.path.join(_jobs_dir(base_dir), f"{job_id}.json")


def _write_job_atomic(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp." + uuid.uuid4().hex[:8]
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass
        raise


def create_job(
    base_dir: str,
    hotel_name: str,
    city: str,
    hotel_id: int = 1,
    fast_demo: bool = False,
) -> str:
    """
    Crea un nuevo job en estado pending. Devuelve el job_id.
    created_at y updated_at se fijan al momento de creación.
    """
    job_id = uuid.uuid4().hex
    now = datetime.utcnow().isoformat() + "Z"
    job = {
        "job_id": job_id,
        "hotel_name": hotel_name,
        "city": city,
        "hotel_id": hotel_id,
        "status": "pending",
        "stage": "created",
        "progress_pct": 0,
        "created_at": now,
        "started_at": None,
        "updated_at": now,
        "completed_at": None,
        "error_message": None,
        "warning_message": None,
        "result_html_path": None,
        "preview_html_path": None,
        "fast_demo": fast_demo,
    }
    path = _job_path(base_dir, job_id)
    _write_job_atomic(path, job)
    return job_id


def update_job(base_dir: str, job_id: str, **kwargs: Any) -> bool:
    """
    Actualiza solo campos permitidos. updated_at se actualiza siempre.
    status, stage y progress_pct se validan con job_schema.
    Cualquier clave no permitida en kwargs → ValueError (no se ignoran en silencio).
    Devuelve True si el job existía y se actualizó.
    """
    reject_unknown_update_keys(kwargs)

    path = _job_path(base_dir, job_id)
    if not os.path.exists(path):
        return False
    try:
        with open(path, encoding="utf-8") as f:
            job = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    now = datetime.utcnow().isoformat() + "Z"
    job["updated_at"] = now

    for k, v in kwargs.items():
        if k == "status":
            job["status"] = validate_status(v)
        elif k == "stage":
            job["stage"] = validate_stage(v)
        elif k == "progress_pct":
            job["progress_pct"] = validate_progress_pct(v)
        else:
            if v is not None or k in NULLABLE_UPDATE_KEYS:
                job[k] = v

    _write_job_atomic(path, job)
    return True


def touch_job(base_dir: str, job_id: str) -> bool:
    """
    Actualiza solo updated_at del job (heartbeat). No modifica status ni stage.
    Devuelve True si el job existía y se actualizó.
    """
    path = _job_path(base_dir, job_id)
    if not os.path.exists(path):
        return False
    try:
        with open(path, encoding="utf-8") as f:
            job = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False
    job["updated_at"] = datetime.utcnow().isoformat() + "Z"
    _write_job_atomic(path, job)
    return True


def get_job(base_dir: str, job_id: str) -> Optional[Dict[str, Any]]:
    """
    Devuelve el job o None si no existe o el archivo está corrupto.
    Solo claves del schema conocido; status/stage/progress_pct normalizados si vienen mal.
    """
    path = _job_path(base_dir, job_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    job = {k: raw[k] for k in JOB_KNOWN_KEYS if k in raw}
    if raw.get("status") not in ALLOWED_STATUSES:
        job["status"] = "failed"
    if raw.get("stage") not in ALLOWED_STAGES:
        job["stage"] = "error" if job.get("status") == "failed" else "done"
    try:
        p = int(job.get("progress_pct", 0))
    except (TypeError, ValueError):
        p = 0
    job["progress_pct"] = min(100, max(0, p))
    return job


def list_recent_jobs(base_dir: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Lista los jobs más recientes por updated_at (desc)."""
    d = _jobs_dir(base_dir)
    if not os.path.isdir(d):
        return []
    jobs = []
    for name in os.listdir(d):
        if not name.endswith(".json") or name.startswith("."):
            continue
        jid = name[:-5]
        j = get_job(base_dir, jid)
        if j:
            jobs.append(j)
    jobs.sort(key=lambda j: j.get("updated_at") or "", reverse=True)
    return jobs[:limit]


def has_active_job_for_hotel(base_dir: str, hotel_name: str) -> Optional[str]:
    """
    Devuelve el job_id de un job activo para el mismo hotel, o None si no hay ninguno.
    Activo = status en ACTIVE_STATUSES (pending, running, rendering, persisting, notifying).
    stalled/completed/failed no bloquean.
    """
    hotel_name_norm = (hotel_name or "").strip()
    if not hotel_name_norm:
        return None
    for j in list_recent_jobs(base_dir, limit=200):
        if (j.get("hotel_name") or "").strip() == hotel_name_norm and j.get("status") in ACTIVE_STATUSES:
            return j.get("job_id")
    return None
