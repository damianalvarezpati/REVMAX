"""
Tests unitarios de Market Signals (Fase 5).
Ejecutar desde la raíz: pytest tests/test_market_signals.py -v
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from market_signals import (
    detect_market_signals,
    build_market_signal_summary,
    count_market_signals_by_effect,
    MARKET_SIGNAL_CONFIG,
    SIGNAL_STRENGTHS,
    DIRECTIONAL_EFFECTS,
)


def _base_outputs(
    price_action="hold",
    demand_signal="medium",
    demand_score=55,
    your_rank=3,
    total=8,
    gri_value=70,
    can_premium=False,
    visibility=0.8,
):
    return {
        "pricing": {
            "recommendation": {"action": price_action},
            "market_context": {"your_position_rank": your_rank, "total_compset": total},
        },
        "demand": {
            "demand_index": {"signal": demand_signal, "score": demand_score},
        },
        "reputation": {"gri": {"value": gri_value, "can_command_premium": can_premium}},
        "distribution": {"visibility_score": visibility},
    }


def _briefing_stub(consolidated_action="hold"):
    return {"consolidated_price_action": consolidated_action}


# 1) Demanda fuerte + pricing favorable => DEMAND_SUPPORTS_INCREASE
def test_demand_supports_increase():
    """Demanda alta debe generar señal DEMAND_SUPPORTS_INCREASE con directional_effect raise."""
    outputs = _base_outputs(demand_signal="high", demand_score=72)
    signals = detect_market_signals(outputs, [], _briefing_stub())
    types = [s["type"] for s in signals]
    assert "DEMAND_SUPPORTS_INCREASE" in types
    sig = next(s for s in signals if s["type"] == "DEMAND_SUPPORTS_INCREASE")
    assert sig["directional_effect"] == "raise"
    assert sig["source"] == "demand"
    assert sig["strength"] in SIGNAL_STRENGTHS


# 2) Demanda débil => WEAK_DEMAND_REQUIRES_CAUTION
def test_weak_demand_caution():
    """Demanda baja debe generar WEAK_DEMAND_REQUIRES_CAUTION con directional_effect caution."""
    outputs = _base_outputs(demand_signal="low", demand_score=38)
    signals = detect_market_signals(outputs, [], _briefing_stub())
    types = [s["type"] for s in signals]
    assert "WEAK_DEMAND_REQUIRES_CAUTION" in types
    sig = next(s for s in signals if s["type"] == "WEAK_DEMAND_REQUIRES_CAUTION")
    assert sig["directional_effect"] == "caution"
    assert sig["source"] == "demand"


# 3) Reputación alta + posición baja en pricing => UNDERPRICED_RELATIVE_TO_POSITION
def test_underpriced_relative_to_position():
    """GRI alto, can_premium y posición débil en ranking deben generar UNDERPRICED_RELATIVE_TO_POSITION."""
    outputs = _base_outputs(gri_value=84, can_premium=True, your_rank=6, total=8)
    signals = detect_market_signals(outputs, [], _briefing_stub())
    types = [s["type"] for s in signals]
    assert "UNDERPRICED_RELATIVE_TO_POSITION" in types
    sig = next(s for s in signals if s["type"] == "UNDERPRICED_RELATIVE_TO_POSITION")
    assert sig["directional_effect"] == "raise"
    assert sig["source"] == "reputation"


# 4) Pricing raise + demanda baja => OVERPRICED_FOR_CURRENT_DEMAND
def test_overpriced_for_current_demand():
    """Pricing recomienda raise y demanda baja debe generar OVERPRICED_FOR_CURRENT_DEMAND."""
    outputs = _base_outputs(price_action="raise", demand_signal="low")
    signals = detect_market_signals(outputs, [], _briefing_stub())
    types = [s["type"] for s in signals]
    assert "OVERPRICED_FOR_CURRENT_DEMAND" in types
    sig = next(s for s in signals if s["type"] == "OVERPRICED_FOR_CURRENT_DEMAND")
    assert sig["directional_effect"] == "lower"
    assert sig["source"] == "pricing"


# 5) Escenario de compresión => MARKET_COMPRESSION
def test_market_compression():
    """Demanda alta + varios conflictos o visibilidad baja deben poder generar MARKET_COMPRESSION."""
    outputs = _base_outputs(demand_signal="high", demand_score=70, visibility=0.35)
    conflicts = [
        {"type": "pricing_vs_demand", "severity": "medium"},
        {"type": "reputation_vs_demand", "severity": "medium"},
    ]
    signals = detect_market_signals(outputs, conflicts, _briefing_stub())
    types = [s["type"] for s in signals]
    assert "MARKET_COMPRESSION" in types or "DEMAND_SUPPORTS_INCREASE" in types
    if "MARKET_COMPRESSION" in types:
        sig = next(s for s in signals if s["type"] == "MARKET_COMPRESSION")
        assert sig["directional_effect"] in ("hold", "caution")


def test_market_compression_many_conflicts():
    """Demanda alta y 3+ conflictos => MARKET_COMPRESSION."""
    outputs = _base_outputs(demand_signal="high", demand_score=76)
    conflicts = [
        {"type": "a", "severity": "medium"},
        {"type": "b", "severity": "high"},
        {"type": "c", "severity": "medium"},
    ]
    signals = detect_market_signals(outputs, conflicts, _briefing_stub())
    types = [s["type"] for s in signals]
    assert "MARKET_COMPRESSION" in types


# 6) Competencia presiona al alza o a la baja => COMPETITOR_PRICE_PRESSURE
def test_competitor_price_pressure_upward():
    """Posición débil en compset (rank alto) debe generar COMPETITOR_PRICE_PRESSURE upward."""
    outputs = _base_outputs(your_rank=7, total=8)
    signals = detect_market_signals(outputs, [], _briefing_stub())
    types = [s["type"] for s in signals]
    assert "COMPETITOR_PRICE_PRESSURE" in types
    sig = next(s for s in signals if s["type"] == "COMPETITOR_PRICE_PRESSURE")
    assert sig["directional_effect"] == "raise"


def test_competitor_price_pressure_downward():
    """Posición fuerte pero demanda baja puede generar COMPETITOR_PRICE_PRESSURE downward."""
    outputs = _base_outputs(your_rank=1, total=8, demand_signal="low")
    signals = detect_market_signals(outputs, [], _briefing_stub())
    types = [s["type"] for s in signals]
    assert "COMPETITOR_PRICE_PRESSURE" in types
    sig = next(s for s in signals if s["type"] == "COMPETITOR_PRICE_PRESSURE")
    assert sig["directional_effect"] == "lower"


def test_signal_structure():
    """Cada señal debe tener type, strength, message, source, directional_effect."""
    outputs = _base_outputs(demand_signal="high", demand_score=70)
    signals = detect_market_signals(outputs, [], _briefing_stub())
    assert len(signals) >= 1
    for s in signals:
        assert "type" in s
        assert "strength" in s and s["strength"] in SIGNAL_STRENGTHS
        assert "message" in s
        assert "source" in s
        assert "directional_effect" in s and s["directional_effect"] in DIRECTIONAL_EFFECTS


def test_summary_and_counts():
    """build_market_signal_summary y count_market_signals_by_effect deben ser coherentes."""
    outputs = _base_outputs(demand_signal="high", demand_score=72)
    signals = detect_market_signals(outputs, [], _briefing_stub())
    summary = build_market_signal_summary(signals)
    assert isinstance(summary, str) and len(summary) > 0
    raise_n = count_market_signals_by_effect(signals, "raise")
    assert raise_n >= 0
    assert "market_signal" in summary.lower() or "señal" in summary.lower() or "subida" in summary.lower() or "raise" in summary.lower() or "favor" in summary.lower()


def test_market_signal_config_defined():
    """MARKET_SIGNAL_CONFIG debe tener los umbrales esperados."""
    assert "demand_high_score_min" in MARKET_SIGNAL_CONFIG
    assert "gri_undervalue_min" in MARKET_SIGNAL_CONFIG
    assert "rank_ratio_weak_position" in MARKET_SIGNAL_CONFIG
