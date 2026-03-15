"""
Tests unitarios del Change Detection Engine (Fase 14).
Ejecutar desde la raíz: pytest tests/test_change_detection_engine.py -v
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from change_detection_engine import (
    build_change_detection,
    CHANGE_SEVERITY_LOW,
    CHANGE_SEVERITY_MEDIUM,
    CHANGE_SEVERITY_HIGH,
)


def _briefing(
    strategy_label="BALANCED",
    derived_overall_status="stable",
    consolidated_price_action="hold",
    alerts=None,
    new_alerts=None,
    resolved_alerts=None,
    strategy_changed=False,
    overall_status_changed=False,
    action_shift=None,
    top_priority_item=None,
    top_value_opportunity=None,
    recommended_scenario="hold",
    opportunities=None,
    recommended_actions=None,
    top_notifications=None,
):
    return {
        "strategy_label": strategy_label,
        "derived_overall_status": derived_overall_status,
        "consolidated_price_action": consolidated_price_action,
        "alerts": alerts or [],
        "new_alerts": new_alerts or [],
        "resolved_alerts": resolved_alerts or [],
        "strategy_changed": strategy_changed,
        "overall_status_changed": overall_status_changed,
        "action_shift": action_shift,
        "top_priority_item": top_priority_item,
        "top_value_opportunity": top_value_opportunity,
        "recommended_scenario": recommended_scenario,
        "opportunities": opportunities or [],
        "recommended_actions": recommended_actions or [],
        "top_notifications": top_notifications or [],
    }


def test_no_previous_run_no_material_changes():
    """Sin corrida previa => change_summary indica que no hay comparación."""
    b = _briefing()
    out = build_change_detection(b, None)
    assert "change_summary" in out
    assert "No previous run" in out["change_summary"] or "first" in out["change_summary"].lower()
    assert out["change_severity"] == CHANGE_SEVERITY_LOW
    assert out["strategy_changed"] is False
    assert out["recommended_scenario_changed"] is False


def test_strategy_changed():
    """Cuando previous tiene otra strategy, strategy_changed True y highlight."""
    prev = {"strategy_label": "BALANCED", "derived_overall_status": "stable", "consolidated_price_action": "hold", "alert_types": [], "top_notification_types": [], "critical_alert_types": [], "high_alert_types": [], "opportunity_types": []}
    b = _briefing(strategy_label="DEFENSIVE", strategy_changed=True)
    out = build_change_detection(b, prev)
    assert out["strategy_changed"] is True
    assert any("Strategy" in h and "DEFENSIVE" in h for h in out["change_highlights"])


def test_new_critical_alert():
    """Nueva alerta crítica => new_critical_alerts y change_severity high."""
    prev = {"alert_types": [], "critical_alert_types": [], "high_alert_types": [], "top_notification_types": [], "strategy_label": "BALANCED", "derived_overall_status": "stable", "consolidated_price_action": "hold", "opportunity_types": []}
    b = _briefing(
        alerts=[{"type": "PARITY_VIOLATION", "severity": "critical", "message": "P", "source": "d"}],
        new_alerts=["PARITY_VIOLATION"],
    )
    out = build_change_detection(b, prev)
    assert "PARITY_VIOLATION" in out["new_critical_alerts"]
    assert out["change_severity"] == CHANGE_SEVERITY_HIGH
    assert out["change_highlights"]


def test_resolved_critical_alert():
    """Alerta crítica resuelta => resolved_critical_alerts."""
    prev = {"alert_types": ["PARITY_VIOLATION"], "critical_alert_types": ["PARITY_VIOLATION"], "high_alert_types": [], "top_notification_types": [], "strategy_label": "BALANCED", "derived_overall_status": "stable", "consolidated_price_action": "hold", "opportunity_types": []}
    b = _briefing(alerts=[], resolved_alerts=["PARITY_VIOLATION"])
    out = build_change_detection(b, prev)
    assert "PARITY_VIOLATION" in out["resolved_critical_alerts"]


def test_top_priority_changed():
    """Cambio de tipo de top_priority_item => top_priority_changed."""
    prev = {"top_priority_item_type": "FIX_PARITY", "strategy_label": "BALANCED", "derived_overall_status": "stable", "consolidated_price_action": "hold", "alert_types": [], "critical_alert_types": [], "high_alert_types": [], "top_notification_types": [], "opportunity_types": []}
    b = _briefing(top_priority_item={"type": "PRICE_INCREASE", "title": "Raise"})
    out = build_change_detection(b, prev)
    assert out["top_priority_changed"] is True
    assert any("priority" in h.lower() for h in out["change_highlights"])


def test_recommended_scenario_changed():
    """Cambio de recommended_scenario => recommended_scenario_changed y scenario_shift."""
    prev = {"recommended_scenario": "raise", "strategy_label": "BALANCED", "derived_overall_status": "stable", "consolidated_price_action": "hold", "alert_types": [], "critical_alert_types": [], "high_alert_types": [], "top_notification_types": [], "opportunity_types": []}
    b = _briefing(recommended_scenario="hold")
    out = build_change_detection(b, prev)
    assert out["recommended_scenario_changed"] is True
    assert out["scenario_shift"] is True
    assert any("scenario" in h.lower() for h in out["change_highlights"])


def test_change_severity_high_when_new_critical():
    """Nueva alerta crítica => change_severity high."""
    prev = {"alert_types": [], "critical_alert_types": [], "high_alert_types": [], "top_notification_types": [], "strategy_label": "BALANCED", "derived_overall_status": "stable", "consolidated_price_action": "hold", "opportunity_types": []}
    b = _briefing(
        alerts=[{"type": "PARITY_VIOLATION", "severity": "critical"}],
        new_alerts=["PARITY_VIOLATION"],
    )
    out = build_change_detection(b, prev)
    assert out["change_severity"] == CHANGE_SEVERITY_HIGH


def test_change_summary_exists():
    """change_summary debe existir siempre."""
    b = _briefing()
    out = build_change_detection(b, None)
    assert "change_summary" in out
    assert isinstance(out["change_summary"], str)

    prev = {"strategy_label": "BALANCED", "derived_overall_status": "stable", "consolidated_price_action": "hold", "alert_types": [], "critical_alert_types": [], "high_alert_types": [], "top_notification_types": [], "opportunity_types": []}
    out2 = build_change_detection(b, prev)
    assert "change_summary" in out2


def test_change_highlights_exists():
    """change_highlights debe existir (lista)."""
    b = _briefing()
    out = build_change_detection(b, None)
    assert "change_highlights" in out
    assert isinstance(out["change_highlights"], list)
