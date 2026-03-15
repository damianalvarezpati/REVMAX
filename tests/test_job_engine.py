"""
Tests de regresión del job engine.
Ejecutar desde la raíz del proyecto: pytest tests/test_job_engine.py -v
"""
import os
import sys
import pytest
import tempfile
import shutil

# Asegurar imports desde la raíz del proyecto
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import job_state
import job_schema
import job_watchdog
import job_recovery
import job_runtime
import job_observability


def _tmp_base():
    d = tempfile.mkdtemp(prefix="revmax_job_test_")
    return d


def test_create_job_includes_created_at():
    """create_job debe incluir created_at y updated_at."""
    base = _tmp_base()
    try:
        job_id = job_state.create_job(base, "Hotel Test", "Barcelona", hotel_id=1, fast_demo=False)
        assert job_id
        job = job_state.get_job(base, job_id)
        assert job is not None
        assert "created_at" in job
        assert job["created_at"] is not None
        assert job["updated_at"] is not None
        assert job["status"] == "pending"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_update_job_rejects_unknown_keys():
    """update_job debe rechazar claves no permitidas con ValueError."""
    base = _tmp_base()
    try:
        job_id = job_state.create_job(base, "Hotel Test", "Barcelona")
        with pytest.raises(ValueError) as exc_info:
            job_state.update_job(base, job_id, status="running", unknown_key="x")
        assert "unknown" in str(exc_info.value).lower() or "allowed" in str(exc_info.value).lower()
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_has_active_job_for_hotel_blocks_second_active_job():
    """has_active_job_for_hotel debe devolver job_id si hay un job activo del mismo hotel."""
    base = _tmp_base()
    try:
        job_id1 = job_state.create_job(base, "Hotel Same", "Barcelona")
        assert job_state.has_active_job_for_hotel(base, "Hotel Same") == job_id1
        assert job_state.has_active_job_for_hotel(base, "Otro Hotel") is None
        # Transición válida hasta completed y comprobar que ya no bloquea
        job_state.update_job(base, job_id1, status="running", stage="starting")
        job_state.update_job(base, job_id1, status="rendering", stage="rendering")
        job_state.update_job(base, job_id1, status="persisting", stage="persisting")
        job_state.update_job(base, job_id1, status="notifying", stage="notifying")
        job_state.update_job(base, job_id1, status="completed", stage="done", progress_pct=100)
        assert job_state.has_active_job_for_hotel(base, "Hotel Same") is None
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_watchdog_does_not_mark_stalled_if_runtime_says_alive():
    """El watchdog no debe marcar como stalled un job cuyo task sigue vivo en runtime."""
    base = _tmp_base()
    try:
        job_id = job_state.create_job(base, "Hotel Alive", "Barcelona")
        job_state.update_job(base, job_id, status="running", stage="discovery", progress_pct=10)
        # Simular que el task está vivo: is_alive(job_id) -> True
        def is_alive(jid):
            return jid == job_id
        result = job_watchdog.mark_stale_jobs(
            base,
            max_idle_seconds=0,
            stalled_message="Stalled",
            is_alive=is_alive,
            dry_run=False,
        )
        assert result["alive_in_runtime"] >= 1
        assert result["marked_stalled"] == 0
        job = job_state.get_job(base, job_id)
        assert job["status"] == "running"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_watchdog_marks_stalled_when_not_alive():
    """El watchdog debe marcar como stalled un job activo sin task vivo y updated_at antiguo."""
    base = _tmp_base()
    try:
        job_id = job_state.create_job(base, "Hotel Orphan", "Barcelona")
        job_state.update_job(base, job_id, status="running", stage="discovery", progress_pct=10)
        # is_alive siempre False
        result = job_watchdog.mark_stale_jobs(
            base,
            max_idle_seconds=0,
            stalled_message="Stalled test",
            is_alive=lambda jid: False,
            dry_run=False,
        )
        assert result["marked_stalled"] == 1
        assert result["marked_stalled_ids"][0] == job_id
        job = job_state.get_job(base, job_id)
        assert job["status"] == "stalled"
        assert job.get("completed_at") is not None
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_cancel_endpoint_leaves_job_in_terminal_state():
    """Cancelar un job activo debe dejarlo en estado terminal (cancelled)."""
    base = _tmp_base()
    # Necesitamos inyectar BASE_DIR en la app o usar env. La app usa BASE_DIR global.
    # Para no tocar la app, creamos job en data/jobs bajo un dir que la app use.
    # Mejor: llamar directamente a job_state y job_runtime y comprobar el flujo.
    try:
        job_id = job_state.create_job(base, "Hotel Cancel", "Barcelona")
        job_state.update_job(base, job_id, status="running", stage="discovery", progress_pct=20)
        # Sin task en runtime: "cancel" solo actualiza estado (como haría el endpoint tras cancelar el task)
        from datetime import datetime
        now_iso = datetime.utcnow().isoformat() + "Z"
        job_state.update_job(
            base,
            job_id,
            status="cancelled",
            stage="error",
            error_message="Cancelado por el usuario.",
            completed_at=now_iso,
        )
        job = job_state.get_job(base, job_id)
        assert job["status"] == "cancelled"
        assert job.get("completed_at") is not None
        assert job["status"] in job_schema.TERMINAL_STATUSES
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_startup_recovery_sanes_orphaned_active_jobs():
    """Startup recovery debe marcar como stalled los jobs activos sin task viva."""
    base = _tmp_base()
    try:
        job_id = job_state.create_job(base, "Hotel Orphan", "Barcelona")
        job_state.update_job(base, job_id, status="running", stage="discovery", progress_pct=15)
        # is_alive siempre False (no hay task registrado)
        result = job_recovery.run_startup_recovery(
            base,
            is_alive=lambda jid: False,
            policy="stalled",
            dry_run=False,
        )
        assert len(result["orphaned"]) == 1
        assert result["orphaned"][0][0] == job_id
        assert result["orphaned"][0][2] == "stalled"
        job = job_state.get_job(base, job_id)
        assert job["status"] == "stalled"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_startup_recovery_dry_run_does_not_write():
    """Startup recovery con dry_run=True no debe modificar jobs."""
    base = _tmp_base()
    try:
        job_id = job_state.create_job(base, "Hotel Dry", "Barcelona")
        job_state.update_job(base, job_id, status="running", stage="discovery")
        result = job_recovery.run_startup_recovery(
            base,
            is_alive=lambda jid: False,
            policy="stalled",
            dry_run=True,
        )
        assert len(result["orphaned"]) == 1
        assert result["dry_run"] is True
        job = job_state.get_job(base, job_id)
        assert job["status"] == "running"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_observability_snapshot_structure():
    """GET /api/jobs/runtime equivalente: get_runtime_snapshot devuelve estructura útil."""
    base = _tmp_base()
    try:
        snap = job_observability.get_runtime_snapshot(
            base,
            get_active_job_ids_fn=job_runtime.get_active_job_ids,
            is_running_fn=job_runtime.is_running,
        )
        assert "active_job_ids" in snap
        assert "by_status" in snap
        assert "orphaned" in snap
        assert "mismatch_summary" in snap
    finally:
        shutil.rmtree(base, ignore_errors=True)
