"""
Business tests: knowledge layer (candidate_rules strong/partial) → deterministic PRO.
"""

from decision_rules_pro import build_deterministic_decision_pro


def _fa_knowledge(**kwargs):
    """Minimal full_analysis with optional knowledge signals in evidence_found."""
    base = {
        "hotel_name": "Hotel Knowledge",
        "evidence_found": {
            "own_price": 100.0,
            "compset_avg": 100.0,
            "price_position": "#5 / 10",
            "demand_score": 60.0,
            "gri": 70.0,
            "visibility": 0.55,
            "parity_status": "ok",
        },
        "agent_outputs": {
            "demand": {"events_detected": []},
            "discovery": {},
            "compset": {},
            "pricing": {},
            "reputation": {},
            "distribution": {},
        },
    }
    ev = dict(base["evidence_found"])
    ev.update(kwargs)
    base["evidence_found"] = ev
    return base


def test_hb001_long_lead_lowers_confidence_vs_short():
    # Mismo perfil "raise" en ambos: la confianza en hold sube si el gap cae (artefacto
    # del término 12-|gap|); aquí forzamos raise para comparar apples-to-apples.
    def _raise_fa(lead):
        return {
            "evidence_found": {
                "own_price": 80.0,
                "compset_avg": 100.0,
                "price_position": "#2 / 10",
                "demand_score": 90.0,
                "gri": 85.0,
                "visibility": 0.8,
                "parity_status": "ok",
                "lead_time_days": lead,
            },
            "agent_outputs": {
                "demand": {"events_detected": ["E1", "E2", "E3", "E4"]},
                "discovery": {},
                "compset": {},
                "pricing": {},
                "reputation": {},
                "distribution": {},
            },
        }

    o_s = build_deterministic_decision_pro(_raise_fa(5))
    o_l = build_deterministic_decision_pro(_raise_fa(200))
    assert o_s["decision"] == "raise" and o_l["decision"] == "raise"
    # HB-001: −6 sobre raise_score bruto; con techo 100 y AB-001 +2 en ambos → 100 vs 96
    assert o_s["scores"]["raise_score"] == 100
    assert o_l["scores"]["raise_score"] == 96
    assert any("HB-001" in r for r in o_l["reasons"])
    ids = {x["id"] for x in o_l["knowledge_applied"]}
    assert "HB-001" in ids


def test_ct001_weekend_reason_and_optional_range_bump_on_raise():
    # Strong raise profile + weekend
    fa = {
        "evidence_found": {
            "own_price": 80.0,
            "compset_avg": 100.0,
            "price_position": "#2 / 10",
            "demand_score": 90.0,
            "gri": 85.0,
            "visibility": 0.8,
            "parity_status": "ok",
            "weekend_context": True,
        },
        "agent_outputs": {
            "demand": {"events_detected": ["E1", "E2", "E3", "E4"]},
            "discovery": {},
            "compset": {},
            "pricing": {},
            "reputation": {},
            "distribution": {},
        },
    }
    out = build_deterministic_decision_pro(fa)
    assert out["decision"] == "raise"
    assert any("CT-001" in r for r in out["reasons"])
    # +1 pp each side vs same without weekend (computed by sibling call)
    fa_nowe = dict(fa)
    fa_nowe["evidence_found"] = {k: v for k, v in fa["evidence_found"].items() if k != "weekend_context"}
    out_base = build_deterministic_decision_pro(fa_nowe)
    assert out["suggested_action"]["range_pct_min"] == out_base["suggested_action"]["range_pct_min"] + 1
    assert out["suggested_action"]["range_pct_max"] == out_base["suggested_action"]["range_pct_max"] + 1


def test_rv001_divergence_guardrail_and_confidence_hit():
    fa = _fa_knowledge(
        reviewer_avg_score_0_10=4.0,
        hotel_avg_review_0_10=8.5,
    )
    fa_base = _fa_knowledge()
    o = build_deterministic_decision_pro(fa)
    o0 = build_deterministic_decision_pro(fa_base)
    assert o["confidence"] < o0["confidence"]
    assert any("RV-001" in g for g in o["guardrails"])
    assert any("RV-001" in r for r in o["reasons"])


def test_ab001_partial_high_price_weak_rep_boosts_lower():
    fa = {
        "evidence_found": {
            "own_price": 140.0,
            "compset_avg": 100.0,
            "price_position": "#9 / 10",
            "demand_score": 20.0,
            "gri": 40.0,
            "visibility": 0.2,
            "parity_status": "ok",
        },
        "agent_outputs": {
            "demand": {"events_detected": []},
            "discovery": {},
            "compset": {},
            "pricing": {},
            "reputation": {},
            "distribution": {},
        },
    }
    out = build_deterministic_decision_pro(fa)
    assert out["decision"] == "lower"
    assert any("AB-001" in r for r in out["reasons"])
    assert any(x["id"] == "AB-001" for x in out["knowledge_applied"])


def test_ota001_secondary_signal_reduces_confidence_slightly():
    fa = _fa_knowledge(ota_search_distance_km=12.5)
    fa0 = _fa_knowledge()
    o = build_deterministic_decision_pro(fa)
    o0 = build_deterministic_decision_pro(fa0)
    assert o["confidence"] <= o0["confidence"]
    assert any("OTA-001" in r and "secondary" in r for r in o["reasons"])


def test_evt001_hypothetical_never_in_knowledge_applied():
    # Any run should not emit EVT-001 (excluded at load)
    out = build_deterministic_decision_pro(_fa_knowledge(lead_time_days=10, weekend_context=True))
    ids = {x["id"] for x in out["knowledge_applied"]}
    assert "EVT-001" not in ids
