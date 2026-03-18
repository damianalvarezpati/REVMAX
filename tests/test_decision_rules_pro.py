import pytest

from decision_rules_pro import build_deterministic_decision_pro


def _full_analysis(
    *,
    own_price,
    compset_avg,
    price_position="#2 / 10",
    demand_score,
    gri,
    visibility,
    parity_status="ok",
    events_count=0,
):
    return {
        "hotel_name": "Hotel Test",
        "evidence_found": {
            "own_price": own_price if own_price is not None else None,
            "compset_avg": compset_avg if compset_avg is not None else None,
            "price_position": price_position,
            "demand_score": demand_score if demand_score is not None else None,
            "gri": gri if gri is not None else None,
            "visibility": visibility if visibility is not None else None,
            "parity_status": parity_status,
        },
        "agent_outputs": {
            "demand": {"events_detected": (["Event"] * int(events_count))},
            "discovery": {},
            "compset": {},
            "pricing": {},
            "reputation": {},
            "distribution": {},
        },
    }


def test_pro_raise_claro():
    full = _full_analysis(
        own_price=80.0,  # muy barato vs 100
        compset_avg=100.0,
        demand_score=90.0,  # muy alta demanda
        gri=85.0,  # strong
        visibility=0.8,  # good
        parity_status="ok",
        events_count=4,
    )
    out = build_deterministic_decision_pro(full)
    assert out["decision"] == "raise"
    assert out["confidence"] >= 70
    assert out["suggested_action"]["primary"].lower().startswith("raise")
    assert out["suggested_action"]["range_pct_min"] >= 1
    assert out["suggested_action"]["range_pct_max"] > out["suggested_action"]["range_pct_min"]


def test_pro_lower_claro():
    full = _full_analysis(
        own_price=140.0,  # muy caro vs 100
        compset_avg=100.0,
        demand_score=20.0,  # muy baja demanda
        gri=35.0,  # poor
        visibility=0.2,  # low
        parity_status="ok",
        events_count=0,
    )
    out = build_deterministic_decision_pro(full)
    assert out["decision"] == "lower"
    assert out["confidence"] >= 70
    assert "lower" in out["suggested_action"]["primary"].lower()
    # range_pct_min/max en "lower" se esperan negativos
    assert out["suggested_action"]["range_pct_min"] < 0
    assert out["suggested_action"]["range_pct_max"] < 0
    assert abs(out["suggested_action"]["range_pct_max"]) >= abs(out["suggested_action"]["range_pct_min"])


def test_pro_hold_parity_violation():
    full = _full_analysis(
        own_price=80.0,
        compset_avg=100.0,
        demand_score=90.0,
        gri=85.0,
        visibility=0.8,
        parity_status="violation",
        events_count=4,
    )
    out = build_deterministic_decision_pro(full)
    assert out["decision"] == "hold"
    assert out["confidence"] <= 35
    assert any(("parity" in g.lower() or "paridad" in g.lower()) for g in out["guardrails"])


def test_pro_hold_falta_datos():
    full = _full_analysis(
        own_price=None,
        compset_avg=None,
        demand_score=None,
        gri=None,
        visibility=None,
        parity_status=None,
        events_count=0,
    )
    out = build_deterministic_decision_pro(full)
    assert out["decision"] == "hold"
    assert out["confidence"] <= 30
    assert "faltan" in out["suggested_action"]["primary"].lower() or "missing" in " ".join(out["reasons"]).lower()


def test_pro_hold_senales_mixtas():
    # aligned + demanda media, reputación weak y visibilidad medium => gap pequeño => hold
    full = _full_analysis(
        own_price=97.0,
        compset_avg=100.0,
        demand_score=60.0,
        gri=48.0,
        visibility=0.4,
        parity_status="ok",
        events_count=0,
    )
    out = build_deterministic_decision_pro(full)
    assert out["decision"] == "hold"
    assert 35 <= out["confidence"] <= 70
    assert out["suggested_action"]["review_in_hours"] in (48, 72)


def test_pro_suggested_action_guardrails_shape():
    full = _full_analysis(
        own_price=80.0,
        compset_avg=100.0,
        demand_score=85.0,
        gri=70.0,
        visibility=0.7,
        parity_status="ok",
        events_count=2,
    )
    out = build_deterministic_decision_pro(full)
    assert out["suggested_action"]["primary"]
    assert isinstance(out["suggested_action"]["review_in_hours"], int)
    assert isinstance(out["guardrails"], list)
    assert out["scores"].keys() >= {"raise_score", "lower_score", "gap"}

