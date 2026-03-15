"""
RevMax — Schema y validación de jobs.
Única definición de estados, etapas y claves permitidas.
Cualquier clave desconocida en update_job se rechaza con ValueError.
"""

from typing import Any, Dict, FrozenSet

ALLOWED_STATUSES: FrozenSet[str] = frozenset({
    "pending",
    "running",
    "rendering",
    "persisting",
    "notifying",
    "completed",
    "failed",
    "stalled",
    "cancelled",
})

# Terminal: job ya no está en ejecución ni bloquea concurrencia
TERMINAL_STATUSES: FrozenSet[str] = frozenset({
    "completed", "failed", "stalled", "cancelled",
})

ALLOWED_STAGES: FrozenSet[str] = frozenset({
    "created",
    "starting",
    "discovery",
    "compset",
    "parallel",
    "pricing",
    "demand",
    "reputation",
    "distribution",
    "consolidate",
    "report",
    "rendering",
    "persisting",
    "notifying",
    "done",
    "error",
})

ALLOWED_UPDATE_KEYS: FrozenSet[str] = frozenset({
    "status",
    "stage",
    "progress_pct",
    "started_at",
    "updated_at",
    "completed_at",
    "error_message",
    "warning_message",
    "result_html_path",
    "preview_html_path",
})

# Estados que bloquean lanzar otro análisis del mismo hotel (no terminales)
ACTIVE_STATUSES: FrozenSet[str] = frozenset({
    "pending",
    "running",
    "rendering",
    "persisting",
    "notifying",
})

# Transiciones de estado permitidas: desde cada estado, solo se puede ir a los del set.
# Evita corrupciones (ej. running -> completed directo).
ALLOWED_TRANSITIONS: Dict[str, FrozenSet[str]] = {
    "pending": frozenset({"running", "cancelled"}),
    "running": frozenset({"rendering", "failed", "cancelled", "stalled"}),
    "rendering": frozenset({"persisting", "failed", "cancelled"}),
    "persisting": frozenset({"notifying", "completed", "failed"}),
    "notifying": frozenset({"completed", "failed"}),
    "completed": frozenset(),
    "failed": frozenset(),
    "cancelled": frozenset(),
    "stalled": frozenset(),
}

NULLABLE_UPDATE_KEYS: FrozenSet[str] = frozenset({
    "error_message",
    "warning_message",
    "result_html_path",
    "preview_html_path",
    "completed_at",
    "started_at",
})


def validate_status(value: Any) -> str:
    s = str(value).strip().lower()
    if s not in ALLOWED_STATUSES:
        raise ValueError(f"status must be one of {sorted(ALLOWED_STATUSES)!r}, got {value!r}")
    return s


def validate_stage(value: Any) -> str:
    s = str(value).strip().lower()
    if s not in ALLOWED_STAGES:
        raise ValueError(f"stage must be one of {sorted(ALLOWED_STAGES)!r}, got {value!r}")
    return s


def validate_progress_pct(value: Any) -> int:
    try:
        p = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"progress_pct must be int 0-100, got {value!r}")
    if not 0 <= p <= 100:
        raise ValueError(f"progress_pct must be 0-100, got {p}")
    return p


def reject_unknown_update_keys(kwargs: dict) -> None:
    """Lanza ValueError si kwargs contiene alguna clave no permitida."""
    unknown = set(kwargs.keys()) - ALLOWED_UPDATE_KEYS
    if unknown:
        raise ValueError(f"unknown job update key(s): {sorted(unknown)!r}. Allowed: {sorted(ALLOWED_UPDATE_KEYS)!r}")
