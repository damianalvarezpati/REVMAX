import pytest


from decision_rules import (
    build_signals_from_pipeline,
    normalize_signals,
    decide,
)


def _full_analysis_example():
    return {
        "hotel_name": "Hotel Test",
        "evidence_found": {
            "own_price": "90.0 €",
            "compset_avg": "100.0",
            "price_position": "#2 / 10",
            "demand_score": "78",
            "gri": "82",
            "visibility": "0.62",
            "parity_status": "ok",
        },
        "agent_outputs": {
            "discovery": {"adr_double": 90.0},
            "compset": {"compset_summary": {"primary_avg_adr": 100.0}},
            "pricing": {"market_context": {"your_position_rank": 2, "total_compset": 10}},
            "demand": {
                "demand_index": {"signal": "high", "score": 78},
                "events_detected": ["ITB Berlin", "Event X"],
            },
            "reputation": {"gri": {"value": 82}},
            "distribution": {
                "visibility_score": 0.62,
                "rate_parity": {"status": "ok"},
            },
        },
    }


def test_mapping_from_evidence_found():
    full = _full_analysis_example()
    signals = build_signals_from_pipeline(full)
    assert signals["own_price"] == pytest.approx(90.0)
    assert signals["compset_avg"] == pytest.approx(100.0)
    assert signals["price_position_rank"] == 2
    assert signals["price_position_total"] == 10
    assert signals["demand_score"] == pytest.approx(78.0)
    assert signals["reputation_gri"] == pytest.approx(82.0)
    assert signals["visibility_score"] == pytest.approx(0.62)
    assert signals["parity_status"] == "ok"
    assert signals["events_present"] is True
    assert signals["events_count"] == 2


def test_rule_raise_price_low_demand_high():
    normalized = normalize_signals(
        {
            "own_price": 90.0,
            "compset_avg": 100.0,
            "demand_score": 75.0,
            "visibility_score": 0.7,
            "parity_status": "ok",
            "events_present": False,
            "events_count": 0,
        }
    )
    out = decide(normalized)
    assert out["decision"] == "raise"
    assert 50 <= out["confidence"] <= 100


def test_rule_lower_price_high_demand_low():
    normalized = normalize_signals(
        {
            "own_price": 110.0,
            "compset_avg": 100.0,
            "demand_score": 30.0,
            "visibility_score": 0.7,
            "parity_status": "ok",
            "events_present": False,
            "events_count": 0,
        }
    )
    out = decide(normalized)
    assert out["decision"] == "lower"
    assert 50 <= out["confidence"] <= 100


def test_hold_by_parity_violation():
    normalized = normalize_signals(
        {
            "own_price": 90.0,
            "compset_avg": 100.0,
            "demand_score": 80.0,
            "visibility_score": 0.7,
            "parity_status": "violation",
            "events_present": False,
            "events_count": 0,
        }
    )
    out = decide(normalized)
    assert out["decision"] == "hold"
    assert out["confidence"] < 50


def test_hold_by_visibility_low_and_price_low():
    normalized = normalize_signals(
        {
            "own_price": 90.0,
            "compset_avg": 100.0,
            "demand_score": 80.0,
            "visibility_score": 0.3,  # low
            "parity_status": "ok",
            "events_present": False,
            "events_count": 0,
        }
    )
    out = decide(normalized)
    assert out["decision"] == "hold"
    assert out["confidence"] < 50


def test_missing_data_defaults_hold_low_confidence():
    normalized = normalize_signals(
        {
            "own_price": None,
            "compset_avg": None,
            "demand_score": None,
            "visibility_score": None,
            "parity_status": None,
            "events_present": False,
            "events_count": 0,
        }
    )
    out = decide(normalized)
    assert out["decision"] == "hold"
    assert out["confidence"] <= 30

