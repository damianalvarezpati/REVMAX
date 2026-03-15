"""
Test de integración: job-status devuelve progress_steps (9 pasos).
Comprueba que la UI puede consumir progress_steps vía /api/job-status/{job_id}.
"""
import os
import sys
import tempfile
import shutil
from unittest.mock import patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
import job_state
import analysis_runner


def _tmp_base():
    return tempfile.mkdtemp(prefix="revmax_progress_test_")


def test_job_status_returns_nine_progress_steps():
    """GET /api/job-status/{job_id} debe incluir progress_steps con 9 elementos."""
    try:
        from fastapi.testclient import TestClient
        from admin_panel import app
    except ImportError:
        pytest.skip("fastapi not installed")
    tmp = _tmp_base()
    try:
        job_id = job_state.create_job(tmp, "Hotel Test", "Barcelona", hotel_id=1, fast_demo=False)
        job_state.update_job(tmp, job_id, status="running", stage="discovery", progress_pct=10)
        steps = [
            {"id": i, "label": f"Step {i}", "status": "done" if i < 2 else "active" if i == 2 else "pending"}
            for i in range(1, 10)
        ]
        analysis_runner.write_job_progress(tmp, job_id, steps)

        with patch("admin_panel.BASE_DIR", tmp):
            client = TestClient(app)
            r = client.get(f"/api/job-status/{job_id}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "progress_steps" in data
        assert len(data["progress_steps"]) == 9
        assert data["status"] == "running"
        assert data["stage"] == "discovery"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_job_status_fallback_nine_steps_when_no_progress_file():
    """Si no hay _progress.json, job-status debe devolver 9 pasos de fallback."""
    try:
        from fastapi.testclient import TestClient
        from admin_panel import app
    except ImportError:
        pytest.skip("fastapi not installed")
    tmp = _tmp_base()
    try:
        job_id = job_state.create_job(tmp, "Hotel Test", "City", hotel_id=1, fast_demo=False)
        job_state.update_job(tmp, job_id, status="running", stage="starting", progress_pct=5)

        with patch("admin_panel.BASE_DIR", tmp):
            client = TestClient(app)
            r = client.get(f"/api/job-status/{job_id}")
        assert r.status_code == 200
        data = r.json()
        assert "progress_steps" in data
        assert len(data["progress_steps"]) == 9
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_build_fallback_progress_steps_nine():
    """analysis_runner.build_fallback_progress_steps devuelve 9 pasos."""
    steps = analysis_runner.build_fallback_progress_steps("discovery", "running", 10)
    assert len(steps) == 9
    assert all("id" in s and "label" in s and "status" in s for s in steps)
    active = [s for s in steps if s["status"] == "active"]
    assert len(active) == 1
