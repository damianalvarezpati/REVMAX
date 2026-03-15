"""
Tests unitarios del Strategy Engine (Fase 3).
Ejecutar desde la raíz: pytest tests/test_strategy.py -v
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from strategy_engine import derive_strategy, apply_strategy_modulation, STRATEGY_CONFIG, STRATEGY_LABELS
from orchestrator import detect_conflicts, consolidate


def _base_outputs(
    price_action="hold",
    demand_signal="medium",
    demand_implication="hold",
    gri_value=70,
    can_premium=False,
    parity_status="ok",
    visibility=0.8,
    your_rank=3,
    total=8,
):
    """Outputs mínimos de agentes para montar escenarios."""
    return {
        "pricing": {
            "recommendation": {"action": price_action},
            "market_context": {"your_position_rank": your_rank, "total_compset": total},
            "confidence_score": 0.7,
        },
        "demand": {
            "demand_index": {"signal": demand_signal, "score": 55},
            "price_implication": demand_implication,
            "confidence_score": 0.65,
        },
        "reputation": {
            "gri": {"value": gri_value, "can_command_premium": can_premium, "suggested_premium_pct": 5 if can_premium else 0},
            "confidence_score": 0.75,
        },
        "distribution": {
            "visibility_score": visibility,
            "rate_parity": {"status": parity_status},
            "confidence_score": 0.65,
        },
        "compset": {"confidence_score": 0.7},
    }


# ─── PREMIUM: reputación fuerte + pricing favorable ─────────────────────────
def test_strategy_premium_strong_reputation_and_pricing():
    """GRI alto, can premium, demanda no baja, pricing raise o posición fuerte => PREMIUM."""
    outputs = _base_outputs(
        price_action="raise",
        demand_signal="medium",
        gri_value=82,
        can_premium=True,
        parity_status="ok",
        your_rank=2,
        total=8,
    )
    conflicts = detect_conflicts(outputs)
    strategy = derive_strategy(outputs, conflicts)
    assert strategy["strategy_label"] == "PREMIUM"
    assert "GRI" in " ".join(strategy["strategy_drivers"]) or "premium" in " ".join(strategy["strategy_drivers"]).lower()
    assert strategy.get("strategy_confidence", 0) >= 0.5


# ─── BALANCED: señales neutras ───────────────────────────────────────────────
def test_strategy_balanced_neutral_signals():
    """Demanda media, sin paridad, sin conflictos high, GRI medio => BALANCED."""
    outputs = _base_outputs(
        price_action="hold",
        demand_signal="medium",
        gri_value=72,
        can_premium=False,
        parity_status="ok",
    )
    conflicts = detect_conflicts(outputs)
    strategy = derive_strategy(outputs, conflicts)
    assert strategy["strategy_label"] == "BALANCED"
    assert "strategy_rationale" in strategy


# ─── DEFENSIVE: demanda baja / conflicto / paridad ───────────────────────────
def test_strategy_defensive_parity_violation():
    """Paridad violada => DEFENSIVE."""
    outputs = _base_outputs(parity_status="violation")
    conflicts = detect_conflicts(outputs)
    strategy = derive_strategy(outputs, conflicts)
    assert strategy["strategy_label"] == "DEFENSIVE"
    assert any("paridad" in d.lower() or "parity" in d.lower() for d in strategy["strategy_drivers"])


def test_strategy_defensive_high_conflict():
    """Conflicto high (pricing raise + demand low) => DEFENSIVE."""
    outputs = _base_outputs(price_action="raise", demand_signal="low", parity_status="ok")
    conflicts = detect_conflicts(outputs)
    strategy = derive_strategy(outputs, conflicts)
    assert strategy["strategy_label"] == "DEFENSIVE"
    assert strategy["strategy_risks"]


# ─── AGGRESSIVE: captación / presión ─────────────────────────────────────────
def test_strategy_aggressive_low_demand_weak_position():
    """Demanda baja y posición débil (rank/total > 0.5) => AGGRESSIVE."""
    outputs = _base_outputs(
        demand_signal="low",
        your_rank=6,
        total=8,
        parity_status="ok",
    )
    conflicts = detect_conflicts(outputs)
    strategy = derive_strategy(outputs, conflicts)
    assert strategy["strategy_label"] == "AGGRESSIVE"
    assert "Demanda" in " ".join(strategy["strategy_drivers"]) or "ocupación" in strategy["strategy_rationale"].lower() or "captación" in strategy["strategy_rationale"].lower()


def test_strategy_aggressive_low_demand_low_visibility():
    """Demanda baja y visibilidad baja => AGGRESSIVE."""
    outputs = _base_outputs(
        demand_signal="low",
        visibility=0.35,
        parity_status="ok",
        your_rank=3,
        total=8,
    )
    conflicts = detect_conflicts(outputs)
    strategy = derive_strategy(outputs, conflicts)
    assert strategy["strategy_label"] == "AGGRESSIVE"


# ─── La estrategia afecta la consolidación ──────────────────────────────────
def test_strategy_affects_consolidation_briefing():
    """El briefing incluye strategy_label, strategy_rationale y strategy_influence_on_decision."""
    outputs = _base_outputs(price_action="raise", demand_signal="medium", gri_value=82, can_premium=True)
    conflicts = detect_conflicts(outputs)
    briefing = consolidate(outputs, conflicts)
    assert "strategy_label" in briefing
    assert briefing["strategy_label"] in STRATEGY_LABELS
    assert "strategy_rationale" in briefing
    assert "strategy_drivers" in briefing
    assert "strategy_risks" in briefing
    assert "strategy_confidence" in briefing
    assert "strategy_influence_on_decision" in briefing


def test_strategy_modulation_defensive_reduces_raise():
    """DEFENSIVE reduce el peso de raise (modulación en señales)."""
    signals = {"raise": 1.0, "hold": 0.5, "lower": 0.0, "promo": 0.0}
    apply_strategy_modulation(signals, "DEFENSIVE", demand_signal="medium", p_action="raise")
    assert signals["raise"] < 1.0
    assert signals["hold"] > 0.5


def test_strategy_modulation_premium_boosts_raise():
    """PREMIUM con p_action raise aumenta el peso de raise."""
    signals = {"raise": 0.8, "hold": 0.7, "lower": 0.0, "promo": 0.0}
    apply_strategy_modulation(signals, "PREMIUM", demand_signal="medium", p_action="raise")
    assert signals["raise"] > 0.8


def test_strategy_config_defined():
    """STRATEGY_CONFIG tiene los umbrales y factores esperados."""
    c = STRATEGY_CONFIG
    assert "gri_min_premium" in c
    assert "defensive_hold_boost" in c
    assert "premium_raise_boost" in c
    assert "aggressive_raise_mult" in c
