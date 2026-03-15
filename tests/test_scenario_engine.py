"""
Tests unitarios del Scenario Engine (Fase 13).
Ejecutar desde la raíz: pytest tests/test_scenario_engine.py -v
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from scenario_engine import (
    build_scenario_assessment,
    SCENARIOS,
    VERDICT_STRONG,
    VERDICT_MEDIUM,
    VERDICT_WEAK,
)


def _briefing(
    consolidated_price_action="hold",
    strategy_label="BALANCED",
    alerts=None,
    market_signals=None,
    demand_score=55,
    demand_signal="medium",
    recommended_actions=None,
):
    return {
        "consolidated_price_action": consolidated_price_action,
        "strategy_label": strategy_label,
        "alerts": alerts or [],
        "market_signals": market_signals or [],
        "demand_score": demand_score,
        "demand_signal": demand_signal,
        "recommended_actions": recommended_actions or [],
    }


def test_demand_strong_underpriced_recommends_raise():
    """Demanda fuerte + underpriced debe recomendar raise."""
    b = _briefing(
        demand_signal="high",
        demand_score=72,
        market_signals=[
            {"type": "DEMAND_SUPPORTS_INCREASE"},
            {"type": "UNDERPRICED_RELATIVE_TO_POSITION"},
        ],
        recommended_actions=[{"type": "PRICE_INCREASE"}],
    )
    out = build_scenario_assessment(b)
    assert out["recommended_scenario"] == "raise"
    raise_a = next(a for a in out["scenario_assessment"] if a["scenario"] == "raise")
    assert raise_a["net_score"] >= out["scenario_assessment"][0]["net_score"] or out["recommended_scenario"] == "raise"


def test_parity_violation_weak_demand_recommends_hold():
    """Parity violation + weak demand debe recomendar hold."""
    b = _briefing(
        alerts=[{"type": "PARITY_VIOLATION", "severity": "critical", "message": "Parity", "source": "distribution"}],
        demand_signal="low",
        demand_score=38,
    )
    out = build_scenario_assessment(b)
    assert out["recommended_scenario"] == "hold"
    hold_a = next(a for a in out["scenario_assessment"] if a["scenario"] == "hold")
    assert hold_a["net_score"] >= 0


def test_weak_demand_overpriced_lower_or_hold():
    """Weak demand + overpriced debe recomendar lower u hold."""
    b = _briefing(
        demand_signal="low",
        demand_score=40,
        market_signals=[{"type": "OVERPRICED_FOR_CURRENT_DEMAND"}],
        alerts=[{"type": "PRICE_TOO_HIGH_FOR_DEMAND", "severity": "high"}],
    )
    out = build_scenario_assessment(b)
    assert out["recommended_scenario"] in ("lower", "hold")
    lower_a = next(a for a in out["scenario_assessment"] if a["scenario"] == "lower")
    assert lower_a["support_score"] >= 1.0


def test_defensive_strategy_penalises_raise():
    """Estrategia DEFENSIVE debe penalizar raise (raise con verdict weak o net negativo si hay alertas)."""
    b = _briefing(
        strategy_label="DEFENSIVE",
        demand_signal="medium",
        demand_score=55,
    )
    out = build_scenario_assessment(b)
    raise_a = next(a for a in out["scenario_assessment"] if a["scenario"] == "raise")
    assert raise_a["risk_score"] >= 1.0
    assert "defensive" in raise_a["reason"].lower() or raise_a["verdict"] == VERDICT_WEAK or raise_a["net_score"] < raise_a["support_score"]


def test_premium_strategy_supports_raise():
    """Estrategia PREMIUM debe apoyar raise (support_score de raise mayor)."""
    b = _briefing(
        strategy_label="PREMIUM",
        demand_signal="high",
        demand_score=68,
        market_signals=[{"type": "UNDERPRICED_RELATIVE_TO_POSITION"}],
    )
    out = build_scenario_assessment(b)
    raise_a = next(a for a in out["scenario_assessment"] if a["scenario"] == "raise")
    assert raise_a["support_score"] >= 1.0
    assert raise_a["net_score"] > 0 or out["recommended_scenario"] == "raise"


def test_scenario_assessment_contains_raise_hold_lower():
    """scenario_assessment debe contener exactamente raise, hold, lower."""
    b = _briefing()
    out = build_scenario_assessment(b)
    scenarios = [a["scenario"] for a in out["scenario_assessment"]]
    assert set(scenarios) == set(SCENARIOS)
    assert len(out["scenario_assessment"]) == 3


def test_net_score_equals_support_minus_risk():
    """Para cada escenario net_score = support_score - risk_score."""
    b = _briefing(
        demand_signal="high",
        market_signals=[{"type": "DEMAND_SUPPORTS_INCREASE"}],
    )
    out = build_scenario_assessment(b)
    for a in out["scenario_assessment"]:
        expected_net = round(a["support_score"] - a["risk_score"], 1)
        assert a["net_score"] == expected_net


def test_recommended_scenario_exists():
    """recommended_scenario debe existir y ser uno de raise, hold, lower."""
    b = _briefing()
    out = build_scenario_assessment(b)
    assert "recommended_scenario" in out
    assert out["recommended_scenario"] in SCENARIOS
    assert "scenario_summary" in out
    assert "scenario_risks" in out
    assert "scenario_tradeoffs" in out
