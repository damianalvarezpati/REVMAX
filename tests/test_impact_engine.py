"""
Tests unitarios del Impact Engine (Fase 11).
Ejecutar desde la raíz: pytest tests/test_impact_engine.py -v
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from impact_engine import (
    build_impact_estimates,
    _get_context,
    _estimate_opportunity_impact,
    _estimate_action_impact,
    IMPACT_CONFIDENCE_LEVELS,
)


def _briefing(
    opportunities=None,
    recommended_actions=None,
    market_signals=None,
    alerts=None,
    strategy_label="BALANCED",
    demand_score=55,
    demand_signal="medium",
    gri_value=70,
    your_rank=5,
    total_compset=10,
):
    return {
        "opportunities": opportunities or [],
        "recommended_actions": recommended_actions or [],
        "market_signals": market_signals or [],
        "alerts": alerts or [],
        "strategy_label": strategy_label,
        "demand_score": demand_score,
        "demand_signal": demand_signal,
        "gri_value": gri_value,
        "your_rank": your_rank,
        "total_compset": total_compset,
    }


def test_impact_for_price_capture_opportunity():
    """PRICE_CAPTURE_OPPORTUNITY con demanda alta y underpriced debe tener impact_estimate y confidence."""
    b = _briefing(
        opportunities=[{"type": "PRICE_CAPTURE_OPPORTUNITY", "opportunity_level": "high", "title": "Capture ADR", "summary": "S", "rationale": "R", "source_items": [], "potential_value": "adr_capture", "recommended_posture": "raise"}],
        market_signals=[{"type": "DEMAND_SUPPORTS_INCREASE"}, {"type": "UNDERPRICED_RELATIVE_TO_POSITION"}],
        demand_score=72,
        demand_signal="high",
    )
    out = build_impact_estimates(b)
    assert out["opportunity_impacts"]
    opp = out["opportunity_impacts"][0]
    assert "impact_estimate" in opp
    assert "impact_confidence" in opp
    assert "impact_reason" in opp
    assert opp["impact_confidence"] in IMPACT_CONFIDENCE_LEVELS
    assert "ADR" in opp["impact_estimate"] or "upside" in opp["impact_estimate"].lower()


def test_impact_for_undervaluation():
    """UNDERVALUATION_OPPORTUNITY debe tener impact_estimate y impact_confidence."""
    b = _briefing(
        opportunities=[{"type": "UNDERVALUATION_OPPORTUNITY", "opportunity_level": "medium", "title": "Under", "summary": "S", "rationale": "R", "source_items": [], "potential_value": "positioning", "recommended_posture": "review"}],
        gri_value=82,
        your_rank=6,
        total_compset=8,
    )
    out = build_impact_estimates(b)
    assert out["opportunity_impacts"]
    opp = out["opportunity_impacts"][0]
    assert "impact_estimate" in opp
    assert "impact_confidence" in opp
    assert "positioning" in opp["impact_estimate"] or "ADR" in opp["impact_estimate"]


def test_impact_for_visibility_recovery():
    """VISIBILITY_RECOVERY_OPPORTUNITY debe tener impact_estimate medium."""
    b = _briefing(
        opportunities=[{"type": "VISIBILITY_RECOVERY_OPPORTUNITY", "opportunity_level": "high", "title": "Visibility", "summary": "S", "rationale": "R", "source_items": [], "potential_value": "visibility", "recommended_posture": "improve_visibility"}],
    )
    out = build_impact_estimates(b)
    assert out["opportunity_impacts"]
    opp = out["opportunity_impacts"][0]
    assert opp.get("impact_confidence") == "medium"
    assert "visibility" in opp["impact_estimate"].lower() or "demand" in opp["impact_estimate"].lower()


def test_impact_for_demand_recovery():
    """DEMAND_RECOVERY_OPPORTUNITY debe tener impact_estimate occupancy protection."""
    b = _briefing(
        opportunities=[{"type": "DEMAND_RECOVERY_OPPORTUNITY", "opportunity_level": "medium", "title": "Demand", "summary": "S", "rationale": "R", "source_items": [], "potential_value": "demand_alignment", "recommended_posture": "hold"}],
    )
    out = build_impact_estimates(b)
    assert out["opportunity_impacts"]
    opp = out["opportunity_impacts"][0]
    assert "impact_estimate" in opp
    assert "Occupancy" in opp["impact_estimate"] or "occupancy" in opp["impact_estimate"]


def test_impact_summary_exists():
    """impact_summary debe existir y ser string."""
    b = _briefing(
        opportunities=[{"type": "PRICE_CAPTURE_OPPORTUNITY", "opportunity_level": "high", "title": "X", "summary": "S", "rationale": "R", "source_items": [], "potential_value": "adr", "recommended_posture": "raise"}],
        recommended_actions=[{"type": "PRICE_INCREASE", "priority": "high", "title": "Raise", "horizon": "this_week", "rationale": "R", "source_signals": [], "expected_effect": "E"}],
    )
    out = build_impact_estimates(b)
    assert "impact_summary" in out
    assert isinstance(out["impact_summary"], str)
    assert len(out["impact_summary"]) > 0


def test_no_crash_if_briefing_empty():
    """Briefing vacío no debe romper."""
    b = _briefing()
    out = build_impact_estimates(b)
    assert "opportunity_impacts" in out
    assert "action_impacts" in out
    assert "impact_summary" in out
    assert "top_value_opportunity" in out
    assert out["opportunity_impacts"] == []
    assert out["action_impacts"] == []


def test_action_impacts_have_estimate_and_confidence():
    """Cada acción en action_impacts debe tener action_impact_estimate y action_impact_confidence."""
    b = _briefing(
        recommended_actions=[
            {"type": "FIX_PARITY", "priority": "urgent", "title": "Fix", "horizon": "immediate", "rationale": "R", "source_signals": [], "expected_effect": "E"},
            {"type": "PRICE_INCREASE", "priority": "high", "title": "Raise", "horizon": "this_week", "rationale": "R", "source_signals": [], "expected_effect": "E"},
        ],
        demand_score=68,
    )
    out = build_impact_estimates(b)
    assert len(out["action_impacts"]) == 2
    for a in out["action_impacts"]:
        assert "action_impact_estimate" in a
        assert "action_impact_confidence" in a
        assert a["action_impact_confidence"] in IMPACT_CONFIDENCE_LEVELS


def test_top_value_opportunity_when_present():
    """Si hay oportunidades, top_value_opportunity debe ser una de ellas."""
    b = _briefing(
        opportunities=[
            {"type": "VISIBILITY_RECOVERY_OPPORTUNITY", "opportunity_level": "medium", "title": "V", "summary": "S", "rationale": "R", "source_items": [], "potential_value": "v", "recommended_posture": "improve"},
            {"type": "PRICE_CAPTURE_OPPORTUNITY", "opportunity_level": "high", "title": "P", "summary": "S", "rationale": "R", "source_items": [], "potential_value": "adr", "recommended_posture": "raise"},
        ],
        demand_score=70,
        market_signals=[{"type": "UNDERPRICED_RELATIVE_TO_POSITION"}],
    )
    out = build_impact_estimates(b)
    assert out["top_value_opportunity"] is not None
    assert out["top_value_opportunity"].get("type") in ("PRICE_CAPTURE_OPPORTUNITY", "VISIBILITY_RECOVERY_OPPORTUNITY")
