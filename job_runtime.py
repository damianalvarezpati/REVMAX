"""
RevMax — Registro en memoria de tasks de análisis activas.
Permite saber si un job_id tiene un task realmente en ejecución.
Alta al arrancar el task, baja al terminar (éxito, fallo o cancelación).
"""

import asyncio
from typing import Dict, List, Optional

_lock = asyncio.Lock()
_registry: Dict[str, asyncio.Task] = {}


async def register(job_id: str, task: asyncio.Task) -> None:
    """Registra un task activo para job_id. Debe llamarse al arrancar el task."""
    async with _lock:
        if job_id in _registry:
            old = _registry[job_id]
            if not old.done():
                old.cancel()
        _registry[job_id] = task


def unregister(job_id: str) -> None:
    """Elimina el registro del job_id. Debe llamarse al terminar el task (success, fail o cancel)."""
    _registry.pop(job_id, None)


def is_running(job_id: str) -> bool:
    """True si hay un task registrado para job_id y aún no ha terminado."""
    task = _registry.get(job_id)
    return task is not None and not task.done()


def get_active_job_ids() -> List[str]:
    """Lista de job_ids con task registrado y no terminado."""
    return [jid for jid, t in _registry.items() if not t.done()]


def get_task(job_id: str) -> Optional[asyncio.Task]:
    """Devuelve el task registrado para job_id o None."""
    return _registry.get(job_id)


def cancel_task(job_id: str) -> bool:
    """
    Cancela el task asociado a job_id si existe y no ha terminado.
    Devuelve True si había un task vivo y se solicitó cancelación.
    El task se dará de baja en unregister cuando termine.
    """
    task = _registry.get(job_id)
    if task is None or task.done():
        return False
    task.cancel()
    return True
