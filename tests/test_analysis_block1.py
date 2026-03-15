"""
Tests Bloque 1: análisis estándar visible (timing, progreso, calidad, evidencias).
Comprueban que analysis_timing, progress_steps, analysis_quality y evidence_found existen
y que no se rompe si faltan datos.
"""
import os
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from orchestrator import (
    _build_progress_steps,
    _build_analysis_quality,
    _build_evidence_found,
    _is_fallback,
    PROGRESS_STEP_LABELS,
)


def test_progress_step_labels_count():
    assert len(PROGRESS_STEP_LABELS) == 9
    for i, (step_id, stage_key, label) in enumerate(PROGRESS_STEP_LABELS):
        assert step_id == i + 1
        assert isinstance(label, str) and len(label) > 0


def test_build_progress_steps_returns_nine():
    steps = _build_progress_steps("discovery", 10, [], False)
    assert len(steps) == 9
    for s in steps:
        assert "id" in s and "label" in s and "status" in s
        assert s["status"] in ("pending", "active", "done", "error", "warning")


def test_build_progress_steps_done_before_current():
    steps = _build_progress_steps("report", 85, [], False)
    done = [s for s in steps if s["status"] == "done"]
    active = [s for s in steps if s["status"] == "active"]
    assert len(active) == 1
    assert active[0]["label"] == "Generando informe final"
    assert len(done) >= 7


def test_build_progress_steps_fallback_marked_warning():
    steps = _build_progress_steps("report", 100, ["discovery", "pricing"], True)
    warnings = [s for s in steps if s["status"] == "warning"]
    assert len(warnings) >= 2


def test_analysis_quality_has_required_keys():
    """analysis_quality debe tener label, score, fallback_count, agents_ok, agents_total, summary."""
    outputs = {k: {"confidence_score": 0.7} for k in ["discovery", "compset", "pricing", "demand", "reputation", "distribution"]}
    q = _build_analysis_quality(outputs, {})
    for key in ("label", "score", "fallback_count", "agents_ok", "agents_fallback", "agents_total", "summary"):
        assert key in q
    assert q["label"] in ("excellent", "good", "degraded", "poor")


def test_build_analysis_quality_structure():
    outputs_ok = {
        "discovery": {"confidence_score": 0.9},
        "compset": {"confidence_score": 0.8},
        "pricing": {"confidence_score": 0.7},
        "demand": {"confidence_score": 0.65},
        "reputation": {"confidence_score": 0.75},
        "distribution": {"confidence_score": 0.65},
    }
    report_ok = {"report_text": "Informe completo."}
    q = _build_analysis_quality(outputs_ok, report_ok)
    assert q["label"] == "excellent"
    assert q["fallback_count"] == 0
    assert q["agents_ok"] == 7
    assert q["agents_total"] == 7
    assert "summary" in q and len(q["summary"]) > 0


def test_build_analysis_quality_degraded():
    outputs = {
        "discovery": {"confidence_score": 0.3},
        "compset": {"confidence_score": 0.3},
        "pricing": {"confidence_score": 0.7},
        "demand": {"confidence_score": 0.65},
        "reputation": {"confidence_score": 0.75},
        "distribution": {"confidence_score": 0.65},
    }
    report = {"report_text": "Informe mínimo."}
    q = _build_analysis_quality(outputs, report)
    assert q["label"] in ("degraded", "good")
    assert q["fallback_count"] >= 2
    assert "summary" in q


def test_is_fallback():
    assert _is_fallback({"confidence_score": 0.3}) is True
    assert _is_fallback({"error": "x"}) is True
    assert _is_fallback({"confidence_score": 0.8}) is False
    assert _is_fallback({}) is False
    assert _is_fallback("not a dict") is True


def test_build_evidence_found_missing_data():
    """No debe romper si faltan discovery, compset, etc."""
    full = {
        "hotel_name": "Hotel Test",
        "agent_outputs": {
            "discovery": {},
            "compset": {},
            "pricing": {},
            "demand": {},
            "reputation": {},
            "distribution": {},
        },
    }
    ev = _build_evidence_found(full)
    assert ev["hotel_detected"] == "No encontrado" or ev["hotel_detected"] == "Hotel Test"
    assert ev["city"] == "No encontrado"
    assert ev["own_price"] == "No encontrado" or "€" in ev["own_price"]
    assert ev["compset_avg"] == "No encontrado"
    assert "top_3_competitors" in ev
    assert ev["is_degraded"] is False


def test_build_evidence_found_with_data():
    full = {
        "hotel_name": "Hotel Arts",
        "agent_outputs": {
            "discovery": {"name": "Hotel Arts Barcelona", "city": "Barcelona", "adr_double": 220.0},
            "compset": {
                "compset_summary": {"primary_avg_adr": 210.0},
                "compset": {"primary": [{"name": "A"}, {"name": "B"}]},
            },
            "pricing": {"market_context": {"your_position_rank": 2, "total_compset": 5}},
            "demand": {"demand_index": {"score": 65}},
            "reputation": {"gri": {"value": 82}},
            "distribution": {"visibility_score": 0.75, "rate_parity": {"status": "ok"}},
        },
    }
    ev = _build_evidence_found(full)
    assert ev["hotel_detected"] == "Hotel Arts Barcelona"
    assert ev["city"] == "Barcelona"
    assert "220" in ev["own_price"]
    assert ev["top_3_competitors"]  # al menos A, B


def test_job_meta_write_read():
    """write_job_meta y read_job_meta persisten y leen meta sin tocar job_state."""
    import analysis_runner
    with tempfile.TemporaryDirectory() as tmp:
        job_id = "test-meta-123"
        analysis_runner.write_job_meta(
            tmp,
            job_id,
            {"discovery_duration": 1.5, "total_duration": 10.0},
            {"label": "good", "score": 0.85, "fallback_count": 0, "agents_ok": 7, "agents_fallback": 0, "agents_total": 7, "summary": "Ok"},
            {"hotel_detected": "Test", "city": "Barcelona"},
            [{"id": 1, "label": "Step 1", "status": "done"}],
        )
        meta = analysis_runner.read_job_meta(tmp, job_id)
        assert meta is not None
        assert meta["analysis_timing"]["total_duration"] == 10.0
        assert meta["analysis_quality"]["label"] == "good"
        assert meta["evidence_found"]["hotel_detected"] == "Test"
        assert len(meta["progress_steps"]) == 1
