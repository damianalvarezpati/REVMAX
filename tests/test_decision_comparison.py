from decision_comparison import build_decision_comparison


def _full_analysis(legacy_action: str, pro_action: str, *, pro_reasons=None, constraints=None, missing=None):
    return {
        "briefing": {"consolidated_price_action": legacy_action},
        "deterministic_decision_pro": {
            "decision": pro_action,
            "reasons": pro_reasons or ["r1", "r2"],
            "constraints_applied": constraints or ["c1"],
            "data_quality": {"critical_missing": missing or []},
        },
    }


def test_comparison_match_true():
    full = _full_analysis("raise", "raise")
    out = build_decision_comparison(full)
    assert out["match"] is True
    assert out["difference_type"] == "same_decision"
    assert out["legacy_decision"] == "raise"
    assert out["deterministic_pro_decision"] == "raise"


def test_comparison_mismatch_raise_vs_hold():
    full = _full_analysis("raise", "hold")
    out = build_decision_comparison(full)
    assert out["match"] is False
    assert out["difference_type"] == "legacy_raise_vs_pro_hold"


def test_comparison_mismatch_hold_vs_lower():
    full = _full_analysis("hold", "lower")
    out = build_decision_comparison(full)
    assert out["difference_type"] == "legacy_hold_vs_pro_lower"


def test_comparison_mismatch_hold_vs_raise():
    full = _full_analysis("hold", "raise")
    out = build_decision_comparison(full)
    assert out["difference_type"] == "legacy_hold_vs_pro_raise"


def test_comparison_mismatch_lower_vs_hold():
    full = _full_analysis("lower", "hold")
    out = build_decision_comparison(full)
    assert out["difference_type"] == "legacy_lower_vs_pro_hold"


def test_comparison_structure_keys():
    full = _full_analysis("raise", "lower", pro_reasons=["why pro"], constraints=["parity_violation"], missing=["visibility_score"])
    out = build_decision_comparison(full)
    assert "legacy_decision" in out
    assert "deterministic_pro_decision" in out
    assert isinstance(out["match"], bool)
    assert "difference_type" in out
    assert isinstance(out["comment"], str)
    assert isinstance(out["legacy_reasons"], list)
    assert isinstance(out["pro_reasons"], list)
    assert isinstance(out["constraints_applied"], list)
    assert isinstance(out["missing_data"], list)

