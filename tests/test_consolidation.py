"""
Tests unitarios de la lógica de consolidación (orchestrator).
Ejecutar desde la raíz: pytest tests/test_consolidation.py -v
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from orchestrator import detect_conflicts, consolidate, CONSOLIDATION_WEIGHTS


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


# ─── 1. Pricing raise + demand low => hold ───────────────────────────────────
def test_raise_plus_demand_low_results_in_hold():
    """Pricing recomienda raise y demanda baja => consolidación debe tender a hold."""
    outputs = _base_outputs(price_action="raise", demand_signal="low", demand_implication="hold")
    conflicts = detect_conflicts(outputs)
    briefing = consolidate(outputs, conflicts)

    assert briefing["consolidated_price_action"] == "hold"
    assert "pricing_vs_demand" in [c["type"] for c in conflicts]
    assert briefing.get("derived_overall_status") in ("alert", "needs_attention")
    assert any("demanda" in d.lower() or "demand" in d.lower() for d in briefing.get("decision_drivers", []))


# ─── 2. Parity violation => hold y urgencia alta en seed ─────────────────────
def test_parity_violation_hold_and_immediate_urgency():
    """Violación de paridad => hold y primera acción en seed con urgency immediate."""
    outputs = _base_outputs(price_action="raise", parity_status="violation")
    conflicts = detect_conflicts(outputs)
    briefing = consolidate(outputs, conflicts)

    assert briefing["consolidated_price_action"] == "hold"
    assert briefing.get("derived_overall_status") == "alert"
    seed = briefing.get("recommended_priority_actions_seed", [])
    assert len(seed) >= 1
    first = seed[0]
    assert first.get("urgency") == "immediate"
    assert "paridad" in first.get("action_hint", "").lower() or "parity" in first.get("action_hint", "").lower()
    assert briefing.get("action_constraints")


# ─── 3. Reputation premium + demand low => conflicto ────────────────────────
def test_reputation_premium_demand_low_conflict():
    """GRI permite premium y demanda baja => debe aparecer conflicto reputation_vs_demand."""
    outputs = _base_outputs(
        demand_signal="low",
        gri_value=82,
        can_premium=True,
    )
    conflicts = detect_conflicts(outputs)
    briefing = consolidate(outputs, conflicts)

    conflict_types = [c["type"] for c in conflicts]
    assert "reputation_vs_demand" in conflict_types
    assert briefing.get("severity_summary") is not None
    assert "high_conflicts" in briefing.get("severity_summary", {})


# ─── 4. Deduplicación de oportunidades ──────────────────────────────────────
def test_opportunity_deduplication():
    """La misma descripción en pricing y demand debe aparecer una sola vez."""
    dup_desc = "Subir suite junior un 5% por demanda alta en fin de semana"
    outputs = _base_outputs()
    outputs["pricing"]["yield_opportunities"] = [{"description": dup_desc}]
    outputs["demand"]["opportunities"] = [{"description": dup_desc}]
    outputs["distribution"]["quick_wins"] = []

    conflicts = detect_conflicts(outputs)
    briefing = consolidate(outputs, conflicts)

    opportunities = briefing.get("opportunities", [])
    assert len(opportunities) == 1, "Misma oportunidad en dos agentes debe deduplicarse a una"
    assert opportunities[0] == dup_desc


# ─── 5. derived_overall_status con critical_issues ──────────────────────────
def test_derived_overall_status_with_critical_issues():
    """Si hay critical_issues (p. ej. paridad o pricing vs demand), derived_overall_status no es stable/strong."""
    outputs = _base_outputs(price_action="raise", demand_signal="low", parity_status="violation")
    conflicts = detect_conflicts(outputs)
    briefing = consolidate(outputs, conflicts)

    assert len(briefing.get("critical_issues", [])) >= 1
    assert briefing.get("derived_overall_status") in ("alert", "needs_attention")
    assert briefing.get("decision_penalties")


def test_derived_overall_status_stable_when_no_issues():
    """Sin conflictos high ni paridad ni demand baja extrema => stable o strong."""
    outputs = _base_outputs(
        price_action="hold",
        demand_signal="high",
        parity_status="ok",
    )
    conflicts = detect_conflicts(outputs)
    briefing = consolidate(outputs, conflicts)

    assert not any(c.get("severity") == "high" for c in conflicts)
    assert briefing.get("derived_overall_status") in ("stable", "strong")


# ─── Pesos centralizados ────────────────────────────────────────────────────
def test_consolidation_weights_defined():
    """CONSOLIDATION_WEIGHTS debe contener los nombres esperados."""
    w = CONSOLIDATION_WEIGHTS
    assert "reputation_premium_raise_factor" in w
    assert "parity_hold_boost" in w
    assert "high_conflict_raise_multiplier" in w
    assert "gri_min_for_premium" in w
    assert "opportunity_max_count" in w
