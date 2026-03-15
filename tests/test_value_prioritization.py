"""
Tests unitarios del Value Prioritization Engine (Fase 12).
Ejecutar desde la raíz: pytest tests/test_value_prioritization.py -v
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from value_prioritization_engine import (
    build_value_prioritization,
    VALUE_SCALE,
    URGENCY_SCALE,
)


def _briefing(
    impact_opportunities=None,
    impact_actions=None,
    alerts=None,
    market_signals=None,
    strategy_label="BALANCED",
    derived_overall_status="stable",
):
    return {
        "impact_opportunities": impact_opportunities or [],
        "impact_actions": impact_actions or [],
        "alerts": alerts or [],
        "market_signals": market_signals or [],
        "strategy_label": strategy_label,
        "derived_overall_status": derived_overall_status,
    }


def test_value_opportunities_exists():
    """El resultado debe incluir value_opportunities con scores y rank."""
    opps = [
        {
            "type": "PRICE_CAPTURE_OPPORTUNITY",
            "title": "Capture ADR",
            "impact_estimate": "ADR capture potential +5% to +10%",
            "impact_confidence": "medium",
        },
    ]
    b = _briefing(impact_opportunities=opps)
    out = build_value_prioritization(b)
    assert "value_opportunities" in out
    assert len(out["value_opportunities"]) == 1
    o = out["value_opportunities"][0]
    assert o.get("type") == "PRICE_CAPTURE_OPPORTUNITY"
    assert o.get("title") == "Capture ADR"
    assert "value_score" in o
    assert "urgency_score" in o
    assert "priority_score" in o
    assert "priority_rank" in o
    assert VALUE_SCALE[0] <= o["value_score"] <= VALUE_SCALE[1]
    assert URGENCY_SCALE[0] <= o["urgency_score"] <= URGENCY_SCALE[1]
    assert o["priority_rank"] == 1


def test_value_actions_exists():
    """El resultado debe incluir value_actions con scores y rank."""
    actions = [
        {
            "type": "FIX_PARITY",
            "title": "Resolve parity",
            "action_impact_estimate": "Restore channel consistency",
            "action_impact_confidence": "high",
        },
    ]
    b = _briefing(impact_actions=actions)
    out = build_value_prioritization(b)
    assert "value_actions" in out
    assert len(out["value_actions"]) == 1
    a = out["value_actions"][0]
    assert a.get("type") == "FIX_PARITY"
    assert "value_score" in a
    assert "urgency_score" in a
    assert "priority_score" in a
    assert "priority_rank" in a
    assert a["priority_rank"] == 1


def test_priority_score_calculated():
    """priority_score debe ser value_score + urgency_score."""
    opps = [{"type": "VISIBILITY_RECOVERY_OPPORTUNITY", "title": "V", "impact_estimate": "Unlock demand", "impact_confidence": "medium"}]
    b = _briefing(impact_opportunities=opps)
    out = build_value_prioritization(b)
    o = out["value_opportunities"][0]
    expected = round(o["value_score"] + o["urgency_score"], 1)
    assert o["priority_score"] == expected


def test_priority_rank_correct():
    """Oportunidades y acciones deben tener priority_rank 1, 2, 3... por priority_score DESC."""
    opps = [
        {"type": "DEMAND_RECOVERY_OPPORTUNITY", "title": "A", "impact_estimate": "X", "impact_confidence": "low"},
        {"type": "PRICE_CAPTURE_OPPORTUNITY", "title": "B", "impact_estimate": "Y", "impact_confidence": "high"},
    ]
    b = _briefing(impact_opportunities=opps)
    out = build_value_prioritization(b)
    ranks = [o["priority_rank"] for o in out["value_opportunities"]]
    assert set(ranks) == {1, 2}
    scores = [o["priority_score"] for o in out["value_opportunities"]]
    assert scores == sorted(scores, reverse=True)


def test_top_priority_item_exists():
    """Si hay oportunidades o acciones, top_priority_item debe existir y tener el mayor priority_score."""
    opps = [{"type": "PRICE_CAPTURE_OPPORTUNITY", "title": "Capture", "impact_estimate": "ADR +5%", "impact_confidence": "medium"}]
    actions = [{"type": "FIX_PARITY", "title": "Fix parity", "action_impact_estimate": "Restore", "action_impact_confidence": "high"}]
    b = _briefing(impact_opportunities=opps, impact_actions=actions)
    out = build_value_prioritization(b)
    assert "top_priority_item" in out
    top = out["top_priority_item"]
    assert top is not None
    assert "priority_score" in top
    assert top.get("item_type") in ("opportunity", "action")
    all_scores = [o["priority_score"] for o in out["value_opportunities"]] + [a["priority_score"] for a in out["value_actions"]]
    assert top["priority_score"] == max(all_scores)


def test_no_crash_if_briefing_empty():
    """Briefing vacío no debe romper; listas vacías y top_priority_item None."""
    b = _briefing()
    out = build_value_prioritization(b)
    assert "value_opportunities" in out
    assert "value_actions" in out
    assert "value_summary" in out
    assert "top_priority_item" in out
    assert out["value_opportunities"] == []
    assert out["value_actions"] == []
    assert out["top_priority_item"] is None
