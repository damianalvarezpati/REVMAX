"""
Tests unitarios de Intelligence Memory (Fase 8).
Ejecutar desde la raíz: pytest tests/test_intelligence_memory.py -v
"""
import os
import sys
import tempfile
import shutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from intelligence_memory import (
    _hotel_slug,
    _build_short_summary,
    save_snapshot,
    load_previous_snapshot,
    compare_with_previous,
    build_memory_bundle,
    STATUS_ORDER,
    ATTENTION_TREND_VALUES,
)


def _briefing(
    strategy_label="BALANCED",
    derived_overall_status="stable",
    consolidated_price_action="hold",
    alerts=None,
    alert_high_count=0,
    alert_critical_count=0,
    market_signals=None,
    recommended_actions=None,
    top_notifications=None,
):
    return {
        "strategy_label": strategy_label,
        "derived_overall_status": derived_overall_status,
        "consolidated_price_action": consolidated_price_action,
        "alerts": alerts or [],
        "alert_high_count": alert_high_count,
        "alert_critical_count": alert_critical_count,
        "market_signals": market_signals or [],
        "recommended_actions": recommended_actions or [],
        "top_notifications": top_notifications or [],
    }


# 1. Primera corrida -> no previous snapshot
def test_first_run_no_previous_snapshot():
    """Primera corrida para un hotel no debe encontrar snapshot previo."""
    base = tempfile.mkdtemp()
    try:
        b = _briefing()
        bundle = build_memory_bundle(b, "Hotel Primera Vez", base)
        assert bundle["previous_snapshot_found"] is False
        assert "memory_snapshot_path" in bundle
        assert os.path.isfile(bundle["memory_snapshot_path"])
        assert bundle["memory_summary"]
        assert bundle["repeated_alerts"] == []
        assert bundle["new_alerts"] == []
        assert bundle["resolved_alerts"] == []
    finally:
        shutil.rmtree(base, ignore_errors=True)


# 2. Segunda corrida con misma alerta -> repeated_alerts
def test_second_run_same_alert_repeated_alerts():
    """Segunda corrida con la misma alerta debe marcar repeated_alerts."""
    base = tempfile.mkdtemp()
    try:
        b1 = _briefing(
            alerts=[{"type": "PARITY_VIOLATION", "severity": "critical"}],
            alert_critical_count=1,
        )
        build_memory_bundle(b1, "Hotel Repetido", base)
        b2 = _briefing(
            alerts=[{"type": "PARITY_VIOLATION", "severity": "critical"}],
            alert_critical_count=1,
        )
        bundle2 = build_memory_bundle(b2, "Hotel Repetido", base)
        assert bundle2["previous_snapshot_found"] is True
        assert "PARITY_VIOLATION" in bundle2["repeated_alerts"]
        assert bundle2["resolved_alerts"] == []
    finally:
        shutil.rmtree(base, ignore_errors=True)


# 3. Alerta nueva -> new_alerts
def test_new_alert_new_alerts():
    """Corrida con alerta que no estaba en la anterior debe marcar new_alerts."""
    base = tempfile.mkdtemp()
    try:
        b1 = _briefing(alerts=[{"type": "LOW_VISIBILITY"}], alert_high_count=0)
        build_memory_bundle(b1, "Hotel Nueva Alerta", base)
        b2 = _briefing(
            alerts=[
                {"type": "LOW_VISIBILITY"},
                {"type": "DEMAND_COLLAPSE"},
            ],
            alert_high_count=1,
        )
        bundle2 = build_memory_bundle(b2, "Hotel Nueva Alerta", base)
        assert bundle2["previous_snapshot_found"] is True
        assert "DEMAND_COLLAPSE" in bundle2["new_alerts"]
    finally:
        shutil.rmtree(base, ignore_errors=True)


# 4. Alerta resuelta -> resolved_alerts
def test_resolved_alert_resolved_alerts():
    """Corrida sin una alerta que existía en la anterior debe marcar resolved_alerts."""
    base = tempfile.mkdtemp()
    try:
        b1 = _briefing(
            alerts=[{"type": "PARITY_VIOLATION"}, {"type": "LOW_VISIBILITY"}],
            alert_critical_count=1,
        )
        build_memory_bundle(b1, "Hotel Resuelto", base)
        b2 = _briefing(alerts=[{"type": "LOW_VISIBILITY"}], alert_critical_count=0)
        bundle2 = build_memory_bundle(b2, "Hotel Resuelto", base)
        assert bundle2["previous_snapshot_found"] is True
        assert "PARITY_VIOLATION" in bundle2["resolved_alerts"]
    finally:
        shutil.rmtree(base, ignore_errors=True)


# 5. Cambio de strategy_label
def test_strategy_label_changed():
    """Cambio de estrategia entre corridas debe marcar strategy_changed."""
    base = tempfile.mkdtemp()
    try:
        b1 = _briefing(strategy_label="BALANCED")
        build_memory_bundle(b1, "Hotel Estrategia", base)
        b2 = _briefing(strategy_label="DEFENSIVE")
        bundle2 = build_memory_bundle(b2, "Hotel Estrategia", base)
        assert bundle2["previous_snapshot_found"] is True
        assert bundle2["strategy_changed"] is True
    finally:
        shutil.rmtree(base, ignore_errors=True)


# 6. Cambio de derived_overall_status
def test_derived_overall_status_changed():
    """Cambio de estado global debe marcar overall_status_changed."""
    base = tempfile.mkdtemp()
    try:
        b1 = _briefing(derived_overall_status="stable")
        build_memory_bundle(b1, "Hotel Estado", base)
        b2 = _briefing(derived_overall_status="alert")
        bundle2 = build_memory_bundle(b2, "Hotel Estado", base)
        assert bundle2["previous_snapshot_found"] is True
        assert bundle2["overall_status_changed"] is True
    finally:
        shutil.rmtree(base, ignore_errors=True)


# 7. attention_trend worsening / improving / stable
def test_attention_trend_worsening():
    """Más alertas o estado más grave debe dar attention_trend worsening."""
    base = tempfile.mkdtemp()
    try:
        b1 = _briefing(derived_overall_status="stable", alert_critical_count=0, alert_high_count=0)
        build_memory_bundle(b1, "Hotel Trend", base)
        b2 = _briefing(derived_overall_status="alert", alert_critical_count=1, alert_high_count=0)
        bundle2 = build_memory_bundle(b2, "Hotel Trend", base)
        assert bundle2["attention_trend"] == "worsening"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_attention_trend_improving():
    """Menos alertas o estado mejor debe dar attention_trend improving."""
    base = tempfile.mkdtemp()
    try:
        b1 = _briefing(derived_overall_status="alert", alert_critical_count=1, alert_high_count=1)
        build_memory_bundle(b1, "Hotel Mejora", base)
        b2 = _briefing(derived_overall_status="stable", alert_critical_count=0, alert_high_count=0)
        bundle2 = build_memory_bundle(b2, "Hotel Mejora", base)
        assert bundle2["attention_trend"] == "improving"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_attention_trend_stable():
    """Sin cambio significativo debe dar attention_trend stable."""
    base = tempfile.mkdtemp()
    try:
        b1 = _briefing(derived_overall_status="stable", alert_critical_count=0, alert_high_count=0)
        build_memory_bundle(b1, "Hotel Estable", base)
        b2 = _briefing(derived_overall_status="stable", alert_critical_count=0, alert_high_count=0)
        bundle2 = build_memory_bundle(b2, "Hotel Estable", base)
        assert bundle2["attention_trend"] == "stable"
        assert bundle2["strategy_changed"] is False
        assert bundle2["overall_status_changed"] is False
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_hotel_slug_safe():
    """_hotel_slug debe producir nombres seguros para carpetas."""
    assert _hotel_slug("Hotel Example") != ""
    assert "/" not in _hotel_slug("Hotel/Name")
    assert _hotel_slug("") == "unknown"


def test_short_summary_contains_key_fields():
    """_build_short_summary debe incluir strategy, status y acción."""
    b = _briefing(strategy_label="DEFENSIVE", derived_overall_status="alert", consolidated_price_action="hold")
    s = _build_short_summary(b)
    assert "DEFENSIVE" in s
    assert "alert" in s
    assert "hold" in s.lower() or "HOLD" in s


def test_compare_with_previous_none():
    """compare_with_previous con previous=None debe devolver valores por defecto."""
    b = _briefing(alerts=[{"type": "X"}])
    out = compare_with_previous(b, None)
    assert out["repeated_alerts"] == []
    assert out["new_alerts"] == []
    assert out["resolved_alerts"] == []
    assert out["strategy_changed"] is False
    assert out["attention_trend"] == "stable"
