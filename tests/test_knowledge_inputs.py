"""Tests: Dojo Knowledge Inputs scoring and structure."""

from knowledge_inputs import compute_knowledge_inputs


def test_knowledge_inputs_nine_areas():
    out = compute_knowledge_inputs(write_snapshot=False)
    assert "error" not in out
    assert len(out["areas"]) == 9
    keys = {a["area_key"] for a in out["areas"]}
    assert keys == {
        "demand",
        "reputation",
        "pricing_context",
        "compset",
        "ota_visibility",
        "events",
        "forecasting",
        "calendar_seasonality",
        "transport_connectivity",
    }


def test_knowledge_inputs_required_fields():
    out = compute_knowledge_inputs(write_snapshot=False)
    for a in out["areas"]:
        assert "coverage_score" in a
        assert "quality_score" in a
        assert "accepted_quality_bonus_points" in a
        assert "knowledge_balance" in a
        assert "recommended_effort_share" in a["knowledge_balance"]
        assert "validation_score" in a
        assert "model_readiness_score" in a
        assert "area_score" in a
        assert a["status_label"] in ("weak", "developing", "usable", "strong")
        assert isinstance(a["missing_gaps"], list)
        assert isinstance(a["suggested_actions"], list)
        assert a["datasets_count"] >= 0
        assert a["rules_supported_count"] >= 0


def test_events_weak_when_only_hypothesis():
    out = compute_knowledge_inputs(write_snapshot=False)
    ev = next(x for x in out["areas"] if x["area_key"] == "events")
    assert ev["hypotheses_pending_count"] >= 1
    assert ev["rules_supported_count"] == 0
    assert ev["status_label"] == "weak"


def test_scoring_notes_present():
    out = compute_knowledge_inputs(write_snapshot=False)
    assert "scoring_notes" in out
    assert "area_score" in out["scoring_notes"]
    assert "dojo_validation_inbox" in out
    assert "global_metrics" in out["dojo_validation_inbox"]
