"""
Tests unitarios del Opportunity Engine (Fase 9).
Ejecutar desde la raíz: pytest tests/test_opportunity_engine.py -v
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from opportunity_engine import (
    build_opportunities,
    build_opportunity_summary,
    count_high_opportunities,
    get_opportunity_types,
    MAX_OPPORTUNITIES,
    OPPORTUNITY_LEVELS,
)


def _briefing(
    strategy_label="BALANCED",
    consolidated_price_action="hold",
    alerts=None,
    market_signals=None,
    recommended_actions=None,
    top_notifications=None,
):
    return {
        "strategy_label": strategy_label,
        "consolidated_price_action": consolidated_price_action,
        "alerts": alerts or [],
        "market_signals": market_signals or [],
        "recommended_actions": recommended_actions or [],
        "top_notifications": top_notifications or [],
    }


def _action(type_, priority="medium", source_signals=None):
    return {"type": type_, "priority": priority, "source_signals": source_signals or []}


# 1. Reputación alta + demanda favorable + underpriced => PRICE_CAPTURE_OPPORTUNITY high
def test_reputation_demand_underpriced_price_capture_high():
    """Reputación alta, demanda favorable y underpriced debe generar PRICE_CAPTURE_OPPORTUNITY high."""
    briefing = _briefing(
        strategy_label="PREMIUM",
        consolidated_price_action="raise",
        market_signals=[
            {"type": "DEMAND_SUPPORTS_INCREASE", "strength": "high", "directional_effect": "raise"},
            {"type": "UNDERPRICED_RELATIVE_TO_POSITION", "strength": "high", "directional_effect": "raise"},
        ],
        recommended_actions=[_action("PRICE_INCREASE", priority="high", source_signals=["DEMAND_SUPPORTS_INCREASE", "UNDERPRICED_RELATIVE_TO_POSITION"])],
    )
    opportunities = build_opportunities(briefing)
    types = [o["type"] for o in opportunities]
    assert "PRICE_CAPTURE_OPPORTUNITY" in types
    opp = next(o for o in opportunities if o["type"] == "PRICE_CAPTURE_OPPORTUNITY")
    assert opp["opportunity_level"] == "high"
    assert "adr_capture" == opp["potential_value"]
    assert "raise" == opp["recommended_posture"]


# 2. Underpriced relativo a posición => UNDERVALUATION_OPPORTUNITY
def test_underpriced_relative_to_position_undervaluation():
    """Underpriced relativo a posición debe generar UNDERVALUATION_OPPORTUNITY."""
    briefing = _briefing(
        consolidated_price_action="hold",
        market_signals=[{"type": "UNDERPRICED_RELATIVE_TO_POSITION", "strength": "medium", "directional_effect": "raise"}],
        recommended_actions=[_action("REVIEW_POSITIONING", source_signals=["UNDERPRICED_RELATIVE_TO_POSITION"])],
    )
    opportunities = build_opportunities(briefing)
    types = [o["type"] for o in opportunities]
    assert "UNDERVALUATION_OPPORTUNITY" in types
    opp = next(o for o in opportunities if o["type"] == "UNDERVALUATION_OPPORTUNITY")
    assert "UNDERPRICED_RELATIVE_TO_POSITION" in opp["source_items"]
    assert opp["potential_value"] == "positioning"


# 3. Strategy defensive + alertas críticas => DEFENSIVE_STABILIZATION_OPPORTUNITY
def test_defensive_critical_alerts_defensive_stabilization():
    """Estrategia DEFENSIVE con alertas críticas debe generar DEFENSIVE_STABILIZATION_OPPORTUNITY."""
    briefing = _briefing(
        strategy_label="DEFENSIVE",
        alerts=[{"type": "PARITY_VIOLATION", "severity": "critical"}],
        recommended_actions=[_action("PROTECT_RATE", priority="urgent"), _action("FIX_PARITY", priority="urgent")],
    )
    opportunities = build_opportunities(briefing)
    types = [o["type"] for o in opportunities]
    assert "DEFENSIVE_STABILIZATION_OPPORTUNITY" in types
    opp = next(o for o in opportunities if o["type"] == "DEFENSIVE_STABILIZATION_OPPORTUNITY")
    assert opp["opportunity_level"] in ("high", "medium")
    assert "strategy_DEFENSIVE" in opp["source_items"]
    assert opp["recommended_posture"] == "hold"


# 4. Low visibility + improve visibility => VISIBILITY_RECOVERY_OPPORTUNITY
def test_low_visibility_improve_visibility_opportunity():
    """LOW_VISIBILITY y acción IMPROVE_VISIBILITY debe generar VISIBILITY_RECOVERY_OPPORTUNITY."""
    briefing = _briefing(
        alerts=[{"type": "LOW_VISIBILITY", "severity": "warning"}],
        recommended_actions=[_action("IMPROVE_VISIBILITY", priority="high", source_signals=["LOW_VISIBILITY"])],
    )
    opportunities = build_opportunities(briefing)
    types = [o["type"] for o in opportunities]
    assert "VISIBILITY_RECOVERY_OPPORTUNITY" in types
    opp = next(o for o in opportunities if o["type"] == "VISIBILITY_RECOVERY_OPPORTUNITY")
    assert opp["opportunity_level"] == "high"
    assert "LOW_VISIBILITY" in opp["source_items"] and "IMPROVE_VISIBILITY" in opp["source_items"]
    assert opp["potential_value"] == "visibility"


# 5. Weak demand + monitor/decrease action => DEMAND_RECOVERY_OPPORTUNITY
def test_weak_demand_monitor_demand_recovery():
    """Demanda débil y acción MONITOR_DEMAND o PRICE_DECREASE debe generar DEMAND_RECOVERY_OPPORTUNITY."""
    briefing = _briefing(
        market_signals=[{"type": "WEAK_DEMAND_REQUIRES_CAUTION", "strength": "high", "directional_effect": "caution"}],
        recommended_actions=[_action("MONITOR_DEMAND", source_signals=["WEAK_DEMAND_REQUIRES_CAUTION"]), _action("HOLD_PRICE")],
    )
    opportunities = build_opportunities(briefing)
    types = [o["type"] for o in opportunities]
    assert "DEMAND_RECOVERY_OPPORTUNITY" in types
    opp = next(o for o in opportunities if o["type"] == "DEMAND_RECOVERY_OPPORTUNITY")
    assert "WEAK_DEMAND_REQUIRES_CAUTION" in opp["source_items"] or "MONITOR_DEMAND" in opp["source_items"]


# 6. Deduplicación y máximo 5 oportunidades
def test_deduplication_max_five_opportunities():
    """Máximo 5 oportunidades; deduplicación por tipo (mayor level gana)."""
    briefing = _briefing(
        strategy_label="PREMIUM",
        consolidated_price_action="raise",
        alerts=[{"type": "LOW_VISIBILITY"}, {"type": "DEMAND_COLLAPSE", "severity": "high"}],
        market_signals=[
            {"type": "DEMAND_SUPPORTS_INCREASE", "strength": "high", "directional_effect": "raise"},
            {"type": "UNDERPRICED_RELATIVE_TO_POSITION", "strength": "high", "directional_effect": "raise"},
            {"type": "WEAK_DEMAND_REQUIRES_CAUTION", "strength": "medium", "directional_effect": "caution"},
        ],
        recommended_actions=[
            _action("PRICE_INCREASE", priority="high"),
            _action("IMPROVE_VISIBILITY", priority="high"),
            _action("MONITOR_DEMAND"),
            _action("PROTECT_RATE", priority="urgent"),
        ],
    )
    opportunities = build_opportunities(briefing)
    assert len(opportunities) <= MAX_OPPORTUNITIES
    types_seen = []
    for o in opportunities:
        assert o["type"] not in types_seen
        types_seen.append(o["type"])
    for o in opportunities:
        assert o.get("type") and o.get("opportunity_level") in OPPORTUNITY_LEVELS
        assert o.get("title") and o.get("summary") and o.get("rationale")
        assert "source_items" in o and "potential_value" in o and "recommended_posture" in o


# 7. opportunity_summary y counts
def test_opportunity_summary_and_counts():
    """build_opportunity_summary, count_high_opportunities y get_opportunity_types deben ser coherentes."""
    opportunities = [
        {"type": "PRICE_CAPTURE_OPPORTUNITY", "opportunity_level": "high", "title": "Capture ADR", "summary": "S", "rationale": "R", "source_items": [], "potential_value": "adr_capture", "recommended_posture": "raise"},
        {"type": "VISIBILITY_RECOVERY_OPPORTUNITY", "opportunity_level": "medium", "title": "Visibility", "summary": "S", "rationale": "R", "source_items": [], "potential_value": "visibility", "recommended_posture": "improve_visibility"},
    ]
    summary = build_opportunity_summary(opportunities)
    assert "alto" in summary or "2" in summary
    assert count_high_opportunities(opportunities) == 1
    assert "PRICE_CAPTURE_OPPORTUNITY" in get_opportunity_types(opportunities)
    assert "VISIBILITY_RECOVERY_OPPORTUNITY" in get_opportunity_types(opportunities)


def test_empty_briefing_no_crash():
    """Briefing mínimo no debe romper; puede devolver lista vacía."""
    opportunities = build_opportunities(_briefing())
    assert isinstance(opportunities, list)
    assert len(opportunities) <= MAX_OPPORTUNITIES


def test_get_opportunity_types_no_unhashable_dict():
    """get_opportunity_types con type dict o mixto no debe lanzar unhashable type: 'dict'."""
    # Si type es un dict (malformado), no debe romper
    opportunities = [
        {"type": "PRICE_CAPTURE_OPPORTUNITY", "opportunity_level": "high", "title": "A", "summary": "S", "rationale": "R", "source_items": [], "potential_value": "v", "recommended_posture": "raise"},
        {"type": {"nested": "dict"}, "opportunity_level": "medium", "title": "B", "summary": "S", "rationale": "R", "source_items": [], "potential_value": "v", "recommended_posture": "hold"},
        {"type": None, "opportunity_level": "low", "title": "C", "summary": "S", "rationale": "R", "source_items": [], "potential_value": "v", "recommended_posture": "hold"},
    ]
    result = get_opportunity_types(opportunities)
    assert isinstance(result, list)
    assert "PRICE_CAPTURE_OPPORTUNITY" in result
    # type dict y None se omiten, no se añaden al set
    assert all(isinstance(x, str) for x in result)
