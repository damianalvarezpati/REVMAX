"""
Tests unitarios del Action Planner / Decision Engine (Fase 6).
Ejecutar desde la raíz: pytest tests/test_action_planner.py -v
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from action_planner import (
    build_recommended_actions,
    build_recommended_action_summary,
    count_actions_by_priority,
    MAX_RECOMMENDED_ACTIONS,
    PRIORITY_ORDER,
    HORIZON_ORDER,
)


def _outputs(price_action="hold", demand_signal="medium", demand_score=55, parity_status="ok", visibility=0.8):
    return {
        "pricing": {"recommendation": {"action": price_action}, "market_context": {"your_position_rank": 3, "total_compset": 8}},
        "demand": {"demand_index": {"signal": demand_signal, "score": demand_score}},
        "reputation": {"gri": {"value": 70}},
        "distribution": {"visibility_score": visibility, "rate_parity": {"status": parity_status}},
    }


def _briefing(consolidated_action="hold", strategy_label="BALANCED", derived_overall_status="stable", alerts=None, market_signals=None):
    b = {
        "consolidated_price_action": consolidated_action,
        "strategy_label": strategy_label,
        "derived_overall_status": derived_overall_status,
        "alerts": alerts or [],
        "market_signals": market_signals or [],
    }
    return b


# 1) Parity violation => FIX_PARITY urgent
def test_parity_violation_fix_parity_urgent():
    """Paridad violada debe generar FIX_PARITY con priority urgent y horizon immediate."""
    outputs = _outputs(parity_status="ok")
    briefing = _briefing(
        alerts=[{"type": "PARITY_VIOLATION", "severity": "critical", "message": "Parity violation", "source": "distribution"}],
    )
    actions = build_recommended_actions(outputs, [], briefing)
    types = [a["type"] for a in actions]
    assert "FIX_PARITY" in types
    fix = next(a for a in actions if a["type"] == "FIX_PARITY")
    assert fix["priority"] == "urgent"
    assert fix["horizon"] == "immediate"
    assert "PARITY_VIOLATION" in fix["source_signals"]


# 2) Underpriced + demand supports increase => PRICE_INCREASE high
def test_underpriced_demand_supports_increase():
    """Underpriced y demanda que soporta subida debe generar PRICE_INCREASE high."""
    outputs = _outputs(price_action="raise", demand_signal="high", demand_score=72)
    briefing = _briefing(
        consolidated_action="raise",
        market_signals=[
            {"type": "DEMAND_SUPPORTS_INCREASE", "strength": "high", "directional_effect": "raise", "source": "demand", "message": "Demand supports raise"},
            {"type": "UNDERPRICED_RELATIVE_TO_POSITION", "strength": "medium", "directional_effect": "raise", "source": "reputation", "message": "Underpriced"},
        ],
    )
    actions = build_recommended_actions(outputs, [], briefing)
    types = [a["type"] for a in actions]
    assert "PRICE_INCREASE" in types
    inc = next(a for a in actions if a["type"] == "PRICE_INCREASE")
    assert inc["priority"] == "high"
    assert "DEMAND_SUPPORTS_INCREASE" in inc["source_signals"] or "UNDERPRICED_RELATIVE_TO_POSITION" in inc["source_signals"]


# 3) Weak demand + overpriced => PRICE_DECREASE high o HOLD_PRICE
def test_weak_demand_overpriced():
    """Demanda débil y señal overpriced debe generar PRICE_DECREASE o HOLD_PRICE coherente."""
    outputs = _outputs(price_action="hold", demand_signal="low", demand_score=38)
    briefing = _briefing(
        consolidated_action="hold",
        alerts=[{"type": "PRICE_TOO_HIGH_FOR_DEMAND", "severity": "high", "message": "Price too high", "source": "pricing"}],
        market_signals=[{"type": "OVERPRICED_FOR_CURRENT_DEMAND", "strength": "high", "directional_effect": "lower", "source": "pricing", "message": "Overpriced"}],
    )
    actions = build_recommended_actions(outputs, [], briefing)
    types = [a["type"] for a in actions]
    assert "PRICE_DECREASE" in types or "HOLD_PRICE" in types
    if "PRICE_DECREASE" in types:
        dec = next(a for a in actions if a["type"] == "PRICE_DECREASE")
        assert dec["priority"] == "high"


# 4) Low visibility => IMPROVE_VISIBILITY
def test_low_visibility_improve_visibility():
    """Alerta LOW_VISIBILITY debe generar IMPROVE_VISIBILITY."""
    outputs = _outputs(visibility=0.4)
    briefing = _briefing(
        alerts=[{"type": "LOW_VISIBILITY", "severity": "warning", "message": "Visibility low", "source": "distribution"}],
    )
    actions = build_recommended_actions(outputs, [], briefing)
    types = [a["type"] for a in actions]
    assert "IMPROVE_VISIBILITY" in types
    vis = next(a for a in actions if a["type"] == "IMPROVE_VISIBILITY")
    assert "LOW_VISIBILITY" in vis["source_signals"]


# 5) Defensive + critical alert => PROTECT_RATE / HOLD_PRICE / FIX_PARITY coherente
def test_defensive_critical_alert():
    """Estrategia DEFENSIVE con alerta crítica debe generar acción coherente (PROTECT_RATE o FIX_PARITY)."""
    outputs = _outputs(parity_status="violation")
    briefing = _briefing(
        strategy_label="DEFENSIVE",
        derived_overall_status="alert",
        alerts=[{"type": "PARITY_VIOLATION", "severity": "critical", "message": "Parity", "source": "distribution"}],
    )
    actions = build_recommended_actions(outputs, [], briefing)
    types = [a["type"] for a in actions]
    assert "FIX_PARITY" in types
    assert any(a["priority"] == "urgent" for a in actions)
    fix = next(a for a in actions if a["type"] == "FIX_PARITY")
    assert fix["priority"] == "urgent"


# 6) Deduplicación y máximo 5 acciones
def test_deduplication_max_five():
    """No más de 5 acciones; por tipo se mantiene la de mayor prioridad."""
    outputs = _outputs(price_action="raise", demand_signal="high", demand_score=78, parity_status="ok", visibility=0.3)
    briefing = _briefing(
        consolidated_action="raise",
        strategy_label="DEFENSIVE",
        derived_overall_status="needs_attention",
        alerts=[
            {"type": "PARITY_VIOLATION", "severity": "critical", "message": "P", "source": "d"},
            {"type": "LOW_VISIBILITY", "severity": "warning", "message": "V", "source": "d"},
            {"type": "DEMAND_COLLAPSE", "severity": "high", "message": "D", "source": "d"},
        ],
        market_signals=[
            {"type": "DEMAND_SUPPORTS_INCREASE", "strength": "high", "directional_effect": "raise", "source": "demand", "message": "M"},
            {"type": "WEAK_DEMAND_REQUIRES_CAUTION", "strength": "medium", "directional_effect": "caution", "source": "demand", "message": "W"},
        ],
    )
    actions = build_recommended_actions(outputs, [], briefing)
    assert len(actions) <= MAX_RECOMMENDED_ACTIONS
    types_seen = []
    for a in actions:
        assert a["type"] not in types_seen
        types_seen.append(a["type"])
    assert "type" in actions[0] and "priority" in actions[0] and "horizon" in actions[0]
    assert "title" in actions[0] and "rationale" in actions[0] and "source_signals" in actions[0] and "expected_effect" in actions[0]


def test_summary_and_counts():
    """build_recommended_action_summary y count_actions_by_priority deben ser coherentes."""
    actions = [
        {"type": "FIX_PARITY", "priority": "urgent", "horizon": "immediate", "title": "Fix parity", "rationale": "R", "source_signals": ["P"], "expected_effect": "E"},
        {"type": "PRICE_INCREASE", "priority": "high", "horizon": "this_week", "title": "Raise", "rationale": "R", "source_signals": ["D"], "expected_effect": "E"},
    ]
    summary = build_recommended_action_summary(actions)
    assert "urgente" in summary or "1" in summary
    assert count_actions_by_priority(actions, "urgent") == 1
    assert count_actions_by_priority(actions, "high") == 1
    assert count_actions_by_priority(actions, "low") == 0


def test_empty_briefing_no_crash():
    """Briefing vacío o sin alertas/signals no debe romper; puede devolver lista vacía o acciones solo por consolidated_action."""
    outputs = _outputs()
    briefing = _briefing(alerts=[], market_signals=[])
    actions = build_recommended_actions(outputs, [], briefing)
    assert isinstance(actions, list)
    assert len(actions) <= MAX_RECOMMENDED_ACTIONS
