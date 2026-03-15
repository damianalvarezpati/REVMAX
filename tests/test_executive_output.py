"""
Tests unitarios de Executive Output Layer (Fase 10).
Ejecutar desde la raíz: pytest tests/test_executive_output.py -v
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from executive_output import (
    build_executive_briefing,
    MAX_TOP_RISKS,
    MAX_TOP_ACTIONS,
    MAX_TOP_OPPORTUNITIES,
    EXECUTIVE_PRIORITY_ORDER,
)


def _briefing(
    strategy_label="BALANCED",
    derived_overall_status="stable",
    consolidated_price_action="hold",
    alerts=None,
    alert_critical_count=0,
    alert_high_count=0,
    recommended_actions=None,
    opportunities=None,
    previous_snapshot_found=False,
    repeated_alerts=None,
    resolved_alerts=None,
    strategy_changed=False,
    overall_status_changed=False,
    attention_trend="stable",
):
    return {
        "strategy_label": strategy_label,
        "derived_overall_status": derived_overall_status,
        "consolidated_price_action": consolidated_price_action,
        "alerts": alerts or [],
        "alert_critical_count": alert_critical_count,
        "alert_high_count": alert_high_count,
        "recommended_actions": recommended_actions or [],
        "opportunities": opportunities or [],
        "previous_snapshot_found": previous_snapshot_found,
        "repeated_alerts": repeated_alerts or [],
        "resolved_alerts": resolved_alerts or [],
        "strategy_changed": strategy_changed,
        "overall_status_changed": overall_status_changed,
        "attention_trend": attention_trend,
    }


def test_executive_summary_seed_exists():
    """build_executive_briefing debe incluir executive_summary_seed con 4 líneas."""
    b = _briefing()
    out = build_executive_briefing(b)
    assert "executive_summary_seed" in out
    seed = out["executive_summary_seed"]
    assert isinstance(seed, list)
    assert len(seed) == 4


def test_top_risks_limited():
    """executive_top_risks debe tener como máximo MAX_TOP_RISKS."""
    b = _briefing(
        alerts=[
            {"type": "A", "severity": "critical", "message": "A"},
            {"type": "B", "severity": "critical", "message": "B"},
            {"type": "C", "severity": "high", "message": "C"},
            {"type": "D", "severity": "high", "message": "D"},
        ],
        alert_critical_count=2,
        alert_high_count=2,
    )
    out = build_executive_briefing(b)
    assert len(out["executive_top_risks"]) <= MAX_TOP_RISKS
    for r in out["executive_top_risks"]:
        assert "type" in r and "severity" in r and "message" in r


def test_top_actions_limited():
    """executive_top_actions debe tener como máximo MAX_TOP_ACTIONS."""
    b = _briefing(
        recommended_actions=[
            {"type": "FIX_PARITY", "priority": "urgent", "title": "Fix", "horizon": "immediate", "rationale": "R"},
            {"type": "PRICE_INCREASE", "priority": "high", "title": "Raise", "horizon": "this_week", "rationale": "R"},
            {"type": "HOLD_PRICE", "priority": "medium", "title": "Hold", "horizon": "this_week", "rationale": "R"},
            {"type": "MONITOR_DEMAND", "priority": "low", "title": "Monitor", "horizon": "monitor", "rationale": "R"},
        ],
    )
    out = build_executive_briefing(b)
    assert len(out["executive_top_actions"]) <= MAX_TOP_ACTIONS


def test_top_opportunities_limited():
    """executive_top_opportunities debe tener como máximo MAX_TOP_OPPORTUNITIES."""
    b = _briefing(
        opportunities=[
            {"type": "PRICE_CAPTURE", "opportunity_level": "high", "title": "Capture", "summary": "S", "recommended_posture": "raise"},
            {"type": "VISIBILITY", "opportunity_level": "high", "title": "Visibility", "summary": "S", "recommended_posture": "improve"},
            {"type": "DEMAND_RECOVERY", "opportunity_level": "medium", "title": "Demand", "summary": "S", "recommended_posture": "hold"},
            {"type": "UNDERVALUATION", "opportunity_level": "medium", "title": "Under", "summary": "S", "recommended_posture": "review"},
        ],
    )
    out = build_executive_briefing(b)
    assert len(out["executive_top_opportunities"]) <= MAX_TOP_OPPORTUNITIES


def test_memory_omitted_when_no_changes():
    """executive_include_memory debe ser False si no hay corrida previa o no hay cambios relevantes."""
    b = _briefing(previous_snapshot_found=False)
    out = build_executive_briefing(b)
    assert out["executive_include_memory"] is False

    b2 = _briefing(previous_snapshot_found=True, repeated_alerts=[], resolved_alerts=[], strategy_changed=False, overall_status_changed=False, attention_trend="stable")
    out2 = build_executive_briefing(b2)
    assert out2["executive_include_memory"] is False


def test_memory_included_when_relevant_changes():
    """executive_include_memory debe ser True si hay corrida previa y repeated_alerts o strategy_changed o attention_trend != stable."""
    b = _briefing(previous_snapshot_found=True, repeated_alerts=["PARITY_VIOLATION"])
    out = build_executive_briefing(b)
    assert out["executive_include_memory"] is True

    b2 = _briefing(previous_snapshot_found=True, strategy_changed=True)
    out2 = build_executive_briefing(b2)
    assert out2["executive_include_memory"] is True

    b3 = _briefing(previous_snapshot_found=True, attention_trend="worsening")
    out3 = build_executive_briefing(b3)
    assert out3["executive_include_memory"] is True


def test_priority_order_consistent():
    """executive_priority_order debe ser la lista fija EXECUTIVE_PRIORITY_ORDER."""
    out = build_executive_briefing(_briefing())
    assert out["executive_priority_order"] == EXECUTIVE_PRIORITY_ORDER
    assert "executive_summary" in out["executive_priority_order"]
    assert "strategic_posture" in out["executive_priority_order"]
    assert "critical_risks" in out["executive_priority_order"]
    assert "recommended_actions" in out["executive_priority_order"]
    assert "opportunities" in out["executive_priority_order"]
    assert "market_context" in out["executive_priority_order"]
    assert "recent_memory" in out["executive_priority_order"]


def test_section_hints_present():
    """executive_section_hints debe contener una entrada por cada sección."""
    out = build_executive_briefing(_briefing())
    hints = out["executive_section_hints"]
    assert isinstance(hints, dict)
    for key in EXECUTIVE_PRIORITY_ORDER:
        assert key in hints
