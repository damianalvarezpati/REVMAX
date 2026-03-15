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


def test_impact_opportunities_exists():
    """El resultado debe incluir impact_opportunities."""
    b = _briefing(
        opportunities=[{"type": "PRICE_CAPTURE_OPPORTUNITY", "opportunity_level": "high", "title": "Capture ADR", "summary": "S", "rationale": "R", "source_items": [], "potential_value": "adr", "recommended_posture": "raise"}],
    )
    out = build_impact_estimates(b)
    assert "impact_opportunities" in out
    assert isinstance(out["impact_opportunities"], list)
    assert len(out["impact_opportunities"]) == 1
    opp = out["impact_opportunities"][0]
    assert "impact_estimate" in opp
    assert "impact_confidence" in opp
    assert "impact_reason" in opp
    assert "type" in opp
    assert "title" in opp
    assert "summary" in opp


def test_impact_actions_exists():
    """El resultado debe incluir impact_actions."""
    b = _briefing(
        recommended_actions=[{"type": "FIX_PARITY", "priority": "urgent", "title": "Fix", "horizon": "immediate", "rationale": "R", "source_signals": [], "expected_effect": "E"}],
    )
    out = build_impact_estimates(b)
    assert "impact_actions" in out
    assert isinstance(out["impact_actions"], list)
    assert len(out["impact_actions"]) == 1
    a = out["impact_actions"][0]
    assert "action_impact_estimate" in a
    assert "action_impact_confidence" in a
    assert "type" in a
    assert "title" in a


def test_impact_summary_exists():
    """impact_summary debe existir y ser string no vacío cuando hay datos."""
    b = _briefing(
        opportunities=[{"type": "PRICE_CAPTURE_OPPORTUNITY", "opportunity_level": "high", "title": "X", "summary": "S", "rationale": "R", "source_items": [], "potential_value": "adr", "recommended_posture": "raise"}],
        recommended_actions=[{"type": "PRICE_INCREASE", "priority": "high", "title": "Raise", "horizon": "this_week", "rationale": "R", "source_signals": [], "expected_effect": "E"}],
    )
    out = build_impact_estimates(b)
    assert "impact_summary" in out
    assert isinstance(out["impact_summary"], str)
    assert len(out["impact_summary"]) > 0


def test_top_value_opportunity_exists():
    """top_value_opportunity debe existir cuando hay oportunidades."""
    b = _briefing(
        opportunities=[{"type": "VISIBILITY_RECOVERY_OPPORTUNITY", "opportunity_level": "high", "title": "V", "summary": "S", "rationale": "R", "source_items": [], "potential_value": "v", "recommended_posture": "improve"}],
    )
    out = build_impact_estimates(b)
    assert "top_value_opportunity" in out
    assert out["top_value_opportunity"] is not None
    assert out["top_value_opportunity"].get("type") == "VISIBILITY_RECOVERY_OPPORTUNITY"


def test_original_opportunities_not_modified():
    """El engine no debe modificar briefing["opportunities"]; el orchestrator no los sobrescribe."""
    opportunities = [{"type": "PRICE_CAPTURE_OPPORTUNITY", "opportunity_level": "high", "title": "T", "summary": "S", "rationale": "R", "source_items": [], "potential_value": "adr", "recommended_posture": "raise"}]
    b = _briefing(opportunities=opportunities)
    impact_results = build_impact_estimates(b)
    b.update(impact_results)
    assert b["opportunities"] is opportunities
    assert "impact_estimate" not in b["opportunities"][0]
    assert b["impact_opportunities"][0].get("impact_estimate")


def test_original_actions_not_modified():
    """El engine no debe modificar briefing["recommended_actions"]; el orchestrator no los sobrescribe."""
    recommended_actions = [{"type": "FIX_PARITY", "priority": "urgent", "title": "Fix", "horizon": "immediate", "rationale": "R", "source_signals": [], "expected_effect": "E"}]
    b = _briefing(recommended_actions=recommended_actions)
    impact_results = build_impact_estimates(b)
    b.update(impact_results)
    assert b["recommended_actions"] is recommended_actions
    assert "action_impact_estimate" not in b["recommended_actions"][0]
    assert b["impact_actions"][0].get("action_impact_estimate")


def test_no_crash_if_briefing_empty():
    """Briefing vacío no debe romper; impact_opportunities e impact_actions deben ser listas vacías."""
    b = _briefing()
    out = build_impact_estimates(b)
    assert "impact_opportunities" in out
    assert "impact_actions" in out
    assert "impact_summary" in out
    assert "top_value_opportunity" in out
    assert out["impact_opportunities"] == []
    assert out["impact_actions"] == []
    assert out["top_value_opportunity"] is None
