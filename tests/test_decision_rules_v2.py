import pytest

from decision_rules_v2 import normalize_signals


def _signals_base(
    *,
    own_price=90.0,
    compset_avg=100.0,
    demand_score=75.0,
    reputation_gri=70.0,
    visibility_score=0.8,
    parity_status="ok",
    events_present=True,
    events_count=2,
):
    return {
        "own_price": own_price,
        "compset_avg": compset_avg,
        "demand_score": demand_score,
        "reputation_gri": reputation_gri,
        "visibility_score": visibility_score,
        "parity_status": parity_status,
        "events_present": events_present,
        "events_count": events_count,
        # se ignoran en v2 pero llegan desde v1 normalize
        "price_position_rank": 2,
        "price_position_total": 10,
        "demand_signal": "medium",
    }


def test_v2_raise_claro():
    signals = _signals_base(own_price=90.0, compset_avg=100.0, demand_score=80.0, visibility_score=0.8)
    normalized = normalize_signals(signals)
    from decision_rules_v2 import decide

    out = decide(normalized)
    assert out["decision"] == "raise"
    assert out["confidence"] >= 60
    assert out["suggested_action"]["primary"].lower().startswith("raise")
    assert out["raise_score"] > out["lower_score"]


def test_v2_lower_claro():
    signals = _signals_base(
        own_price=125.0,
        compset_avg=100.0,
        demand_score=30.0,
        reputation_gri=40.0,
        visibility_score=0.4,
        parity_status="ok",
        events_present=False,
        events_count=0,
    )
    normalized = normalize_signals(signals)
    from decision_rules_v2 import decide

    out = decide(normalized)
    assert out["decision"] == "lower"
    assert out["confidence"] >= 60
    assert "lower" in out["suggested_action"]["primary"].lower()
    assert out["lower_score"] > out["raise_score"]


def test_v2_hold_por_parity_violation():
    signals = _signals_base(own_price=90.0, compset_avg=100.0, parity_status="violation", demand_score=85.0)
    normalized = normalize_signals(signals)
    from decision_rules_v2 import decide

    out = decide(normalized)
    assert out["decision"] == "hold"
    assert out["confidence"] <= 30


def test_v2_hold_por_falta_de_datos():
    signals = _signals_base(own_price=None, compset_avg=100.0, demand_score=None, visibility_score=None)
    normalized = normalize_signals(signals)
    from decision_rules_v2 import decide

    out = decide(normalized)
    assert out["decision"] == "hold"
    assert out["confidence"] <= 30
    assert "faltan datos" in out["suggested_action"]["primary"].lower()


def test_v2_hold_senales_mixtas():
    # precio sugiere raise, pero demanda/reputación empujan a lower => hold por gap insuficiente
    signals = _signals_base(
        own_price=90.0,
        compset_avg=100.0,
        demand_score=45.0,   # low
        reputation_gri=30.0, # poor
        visibility_score=0.5, # medium
        events_present=False,
        events_count=0,
    )
    normalized = normalize_signals(signals)
    from decision_rules_v2 import decide

    out = decide(normalized)
    assert out["decision"] == "hold"
    assert out["confidence"] >= 30
    assert 0 <= out["confidence"] <= 70


def test_v2_suggested_action_razonable_para_hold():
    signals = _signals_base(
        own_price=90.0,
        compset_avg=100.0,
        demand_score=45.0,    # mixed con reputación pobre => gap insuficiente => hold
        reputation_gri=30.0,
        visibility_score=0.5,
        events_present=False,
        events_count=0,
    )
    normalized = normalize_signals(signals)
    from decision_rules_v2 import decide

    out = decide(normalized)
    assert out["decision"] == "hold"
    assert out["suggested_action"]["review_in_hours"] in (48, 72)

