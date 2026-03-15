"""
Tests de robustez para agentes 1-6: parse seguro, fallback mínimo, contrato para pipeline.
Comprueban: JSON válido, texto+JSON, JSON roto, truncado, respuesta vacía, fallback con claves requeridas.
"""
import os
import sys
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from agents.agent_parse_utils import parse_json_response

# Fallbacks y contratos mínimos
from agents.agent_01_discovery import _build_minimal_discovery_fallback
from agents.agent_02_compset import _build_minimal_compset_fallback
from agents.agent_03_pricing import _build_minimal_pricing_fallback
from agents.agent_04_demand import _build_minimal_demand_fallback
from agents.agent_05_reputation import _build_minimal_reputation_fallback
from agents.agent_06_distribution import _build_minimal_distribution_fallback


# ─── parse_json_response (usado por todos) ──────────────────────────────────

def test_parse_valid_json():
    raw = json.dumps({"a": 1, "b": "x", "name": "Hotel"})
    result, err = parse_json_response(raw)
    assert err is None
    assert result == {"a": 1, "b": "x", "name": "Hotel"}


def test_parse_text_plus_json():
    raw = "Aquí tienes el resultado:\n\n" + json.dumps({"name": "X", "adr_double": 100})
    result, err = parse_json_response(raw)
    assert err is None
    assert result.get("name") == "X" and result.get("adr_double") == 100


def test_parse_broken_json_returns_error():
    raw = '{"name": "X", "missing": comma}'
    result, err = parse_json_response(raw)
    assert result is None
    assert err is not None and len(err) > 0


def test_parse_truncated_returns_error_or_partial():
    raw = '{"name": "X", "nested": {"a": 1'
    result, err = parse_json_response(raw)
    if result is None:
        assert err is not None
    else:
        assert isinstance(result, dict)


def test_parse_empty_returns_error():
    result, err = parse_json_response("")
    assert result is None
    assert err is not None


def test_parse_non_dict_root_returns_error():
    result, err = parse_json_response("[1, 2, 3]")
    assert result is None
    assert err is not None


# ─── Discovery fallback ──────────────────────────────────────────────────────

def test_discovery_fallback_has_required_keys():
    fallback = _build_minimal_discovery_fallback("Hotel Test", "Barcelona")
    required = ["name", "adr_double", "primary_segment", "discovery_metadata", "reputation", "channels", "zone", "booking_score"]
    for k in required:
        assert k in fallback, f"discovery fallback missing: {k}"
    assert isinstance(fallback["adr_double"], (int, float))
    assert isinstance(fallback["discovery_metadata"], dict)
    assert fallback["discovery_metadata"].get("confidence_score") == 0.3
    assert fallback["name"] == "Hotel Test"
    assert fallback["city"] == "Barcelona"


def test_discovery_fallback_empty_hotel_name():
    fallback = _build_minimal_discovery_fallback("", "")
    assert fallback["name"] == "Hotel"
    assert "adr_double" in fallback


# ─── Compset fallback ────────────────────────────────────────────────────────

def test_compset_fallback_has_required_keys():
    profile = {"name": "H", "adr_double": 150.0, "primary_segment": "leisure"}
    market = {"candidates": []}
    fallback = _build_minimal_compset_fallback(profile, market)
    assert "compset" in fallback
    assert "primary" in fallback["compset"]
    assert "aspirational" in fallback["compset"]
    assert "surveillance" in fallback["compset"]
    assert "compset_summary" in fallback
    assert "primary_avg_adr" in fallback["compset_summary"]
    assert fallback["compset_summary"]["primary_avg_adr"] == 150.0
    assert fallback["confidence_score"] == 0.3


def test_compset_fallback_adr_question_mark():
    profile = {"name": "H", "adr_double": "?", "primary_segment": "mixed"}
    fallback = _build_minimal_compset_fallback(profile, {})
    assert fallback["compset_summary"]["primary_avg_adr"] == 100.0


# ─── Pricing fallback ───────────────────────────────────────────────────────

def test_pricing_fallback_has_required_keys():
    profile = {"name": "H", "adr_double": 120.0}
    compset = {"compset_summary": {"primary_avg_adr": 125.0}, "compset": {"primary": []}}
    demand = {"demand_index": {"signal": "medium", "score": 50}, "events_detected": []}
    fallback = _build_minimal_pricing_fallback(profile, compset, demand)
    assert fallback["recommendation"]["action"] == "hold"
    assert "market_context" in fallback
    assert "your_position_rank" in fallback["market_context"]
    assert "total_compset" in fallback["market_context"]
    assert "indices" in fallback
    assert "ari" in fallback["indices"]
    assert "rgi" in fallback["indices"]
    assert fallback["confidence_score"] == 0.3


# ─── Demand fallback ────────────────────────────────────────────────────────

def test_demand_fallback_has_required_keys():
    profile = {"name": "H"}
    compset = {}
    fallback = _build_minimal_demand_fallback(profile, compset)
    assert fallback["demand_index"]["score"] == 50
    assert fallback["demand_index"]["signal"] == "medium"
    assert fallback["price_implication"] == "hold"
    assert "events_detected" in fallback
    assert isinstance(fallback["events_detected"], list)
    assert "forecast" in fallback
    assert "next_7_days" in fallback["forecast"]
    assert fallback["confidence_score"] == 0.3


# ─── Reputation fallback ────────────────────────────────────────────────────

def test_reputation_fallback_has_required_keys():
    profile = {"name": "H"}
    compset = {}
    fallback = _build_minimal_reputation_fallback(profile, compset)
    assert fallback["gri"]["value"] == 70.0
    assert fallback["gri"]["can_command_premium"] is False
    assert "recent_negative_themes" in fallback
    assert "sentiment_analysis" in fallback
    assert (fallback.get("sentiment_analysis") or {}).get("price_perception") == "neutral"
    assert fallback["confidence_score"] == 0.3


# ─── Distribution fallback ────────────────────────────────────────────────────

def test_distribution_fallback_has_required_keys():
    profile = {"name": "H"}
    compset = {}
    fallback = _build_minimal_distribution_fallback(profile, compset)
    assert fallback["rate_parity"]["status"] == "ok"
    assert "visibility_score" in fallback
    assert fallback["visibility_score"] == 0.5
    assert "quick_wins" in fallback
    assert isinstance(fallback["quick_wins"], list)
    assert fallback["confidence_score"] == 0.3


# ─── Integración: consolidate acepta outputs con fallbacks ───────────────────

def test_consolidate_accepts_all_fallbacks():
    """El orquestador consolidate() debe poder ejecutarse con todos los agentes en fallback."""
    from orchestrator import detect_conflicts, consolidate

    profile = {"name": "Hotel Fallback", "adr_double": 100.0, "primary_segment": "mixed"}
    compset = _build_minimal_compset_fallback(profile, {"candidates": []})
    demand = _build_minimal_demand_fallback(profile, compset)
    reputation = _build_minimal_reputation_fallback(profile, compset)
    distribution = _build_minimal_distribution_fallback(profile, compset)
    pricing = _build_minimal_pricing_fallback(profile, compset, demand)

    outputs = {
        "discovery": _build_minimal_discovery_fallback("Hotel Fallback", "City"),
        "compset": compset,
        "pricing": pricing,
        "demand": demand,
        "reputation": reputation,
        "distribution": distribution,
    }
    conflicts = detect_conflicts(outputs)
    briefing = consolidate(outputs, conflicts)
    assert "consolidated_price_action" in briefing
    assert briefing["consolidated_price_action"] in ("raise", "hold", "lower", "promo")
    assert "derived_overall_status" in briefing
    assert "recommended_priority_actions_seed" in briefing
