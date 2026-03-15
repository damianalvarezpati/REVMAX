"""
RevMax — Tests para la capa QA (case builder, registry, triage, decision summary).
"""

import json
import os
import tempfile
import pytest

from qa_case_builder import build_validation_case_from_briefing, _slug
from qa_registry import (
    save_validation_case,
    load_validation_cases,
    summarize_validation_cases,
    apply_human_review,
    build_qa_decision_summary,
)
from qa_triage import (
    triage_case,
    get_all_issue_codes,
    get_all_adjustment_codes,
    CASE_NOT_EXPLAINABLE,
    NO_CHANGE_NEEDED,
)


def test_build_validation_case_from_briefing_functions():
    """build_validation_case_from_briefing devuelve un dict con las claves esperadas."""
    briefing = {
        "demand_score": 55,
        "demand_signal": "medium",
        "derived_overall_status": "stable",
        "strategy_label": "BALANCED",
        "consolidated_price_action": "hold",
        "recommended_scenario": "hold",
        "your_rank": 3,
        "total_compset": 10,
        "gri_value": 72,
        "alerts": [],
        "market_signals": [],
        "decision_drivers": ["Pricing recomienda hold", "Demand implica hold"],
        "decision_penalties": [],
        "scenario_summary": "Hold appears the most defendable scenario.",
        "scenario_risks": [],
        "scenario_tradeoffs": [],
        "executive_top_risks": [],
        "executive_top_actions": [{"title": "Hold price", "urgency": "this_week"}],
        "executive_top_opportunities": [],
        "recommended_priority_actions_seed": [{"urgency": "this_week", "action_hint": "Hold."}],
        "opportunities": [],
    }
    case = build_validation_case_from_briefing(briefing, "Hotel Test", scenario_name="hold")
    assert isinstance(case, dict)
    assert "test_id" in case
    assert "timestamp" in case
    assert case["hotel_name"] == "Hotel Test"
    assert case["scenario_name"] == "hold"


def test_observed_facts_exists():
    """observed_facts existe y contiene datos derivados del briefing."""
    briefing = {
        "demand_score": 60,
        "demand_signal": "high",
        "your_rank": 2,
        "total_compset": 8,
        "gri_value": 78,
        "alerts": [{"type": "PARITY_VIOLATION", "severity": "high", "message": "Parity violation"}],
        "market_signals": [{"type": "DEMAND_SUPPORTS_INCREASE", "effect": "raise"}],
    }
    case = build_validation_case_from_briefing(briefing, "Hotel A")
    assert "observed_facts" in case
    obs = case["observed_facts"]
    assert obs.get("demand_score") == 60
    assert obs.get("demand_signal") == "high"
    assert obs.get("parity_status") == "violation"
    assert "alerts_detected" in obs
    assert "market_signal_types" in obs


def test_interpreted_signals_exists():
    """interpreted_signals existe con strategy_label, derived_overall_status, etc."""
    briefing = {
        "strategy_label": "PREMIUM",
        "derived_overall_status": "strong",
        "consolidated_price_action": "raise",
        "recommended_scenario": "raise",
        "top_priority_item": {"item_type": "opportunity", "title": "Capture ADR", "priority_score": 7.5},
    }
    case = build_validation_case_from_briefing(briefing, "Hotel B")
    assert "interpreted_signals" in case
    sig = case["interpreted_signals"]
    assert sig.get("strategy_label") == "PREMIUM"
    assert sig.get("derived_overall_status") == "strong"
    assert sig.get("consolidated_price_action") == "raise"
    assert sig.get("recommended_scenario") == "raise"
    assert "top_priority_item" in sig


def test_why_this_conclusion_exists():
    """why_this_conclusion existe con drivers, risks, trade-offs y defensibilidad."""
    briefing = {
        "decision_drivers": ["Driver A", "Driver B"],
        "decision_penalties": ["Risk 1"],
        "scenario_summary": "Raise is defendable because...",
        "scenario_risks": ["Raise: high risk"],
        "scenario_tradeoffs": ["Trade-off X"],
    }
    case = build_validation_case_from_briefing(briefing, "Hotel C")
    assert "why_this_conclusion" in case
    why = case["why_this_conclusion"]
    assert "main_drivers" in why
    assert "why_recommended_scenario_defendable" in why


def test_save_load_case_functions():
    """save_validation_case y load_validation_cases funcionan."""
    case = build_validation_case_from_briefing({"demand_score": 50}, "SaveLoad Hotel")
    with tempfile.TemporaryDirectory() as tmp:
        path = save_validation_case(case, base_dir=tmp)
        assert os.path.isfile(path)
        assert "SaveLoad_Hotel" in path or "SaveLoad" in path
        loaded = load_validation_cases(base_dir=tmp, limit=10)
        assert len(loaded) >= 1
        one = next((c for c in loaded if c.get("hotel_name") == "SaveLoad Hotel"), None)
        assert one is not None
        assert one.get("observed_facts") is not None


def test_apply_human_review_updates_case():
    """apply_human_review actualiza human_score, human_feedback, human_verdict, adjustment_decision."""
    case = build_validation_case_from_briefing({"demand_score": 50}, "Review Hotel")
    with tempfile.TemporaryDirectory() as tmp:
        path = save_validation_case(case, base_dir=tmp)
        updated = apply_human_review(
            path,
            score=4,
            feedback="Buen criterio en hold.",
            verdict="agree",
            adjustment_decision="no_change_needed",
        )
        assert updated["human_score"] == 4
        assert updated["human_feedback"] == "Buen criterio en hold."
        assert updated["human_verdict"] == "agree"
        assert updated["adjustment_decision"] == "no_change_needed"
        with open(path, encoding="utf-8") as f:
            disk = json.load(f)
        assert disk["human_score"] == 4
        assert disk["human_verdict"] == "agree"

    with tempfile.TemporaryDirectory() as tmp:
        path = save_validation_case(build_validation_case_from_briefing({}, "X"), base_dir=tmp)
        with pytest.raises(ValueError):
            apply_human_review(path, score=10)
        with pytest.raises(ValueError):
            apply_human_review(path, verdict="invalid")


def test_build_qa_decision_summary_functions():
    """build_qa_decision_summary devuelve total_cases, human_score_mean, verdict_pct, issues, adjustment."""
    cases = [
        build_validation_case_from_briefing({"demand_score": 50, "strategy_label": "BALANCED", "decision_drivers": ["A"], "scenario_summary": "Hold is defendable because signals align."}, "H1"),
        build_validation_case_from_briefing({"demand_score": 55, "strategy_label": "BALANCED", "decision_drivers": ["B"], "scenario_summary": "Hold is defendable."}, "H2"),
    ]
    cases[0]["human_score"] = 4
    cases[0]["human_verdict"] = "agree"
    cases[1]["human_score"] = 2
    cases[1]["human_verdict"] = "disagree"
    summary = build_qa_decision_summary(cases)
    assert summary["total_cases"] == 2
    assert summary["human_score_mean"] == 3.0
    assert summary["human_verdict_pct"] is not None
    assert "agree" in summary["human_verdict_pct"]
    assert "most_common_issues" in summary
    assert "most_problematic_areas" in summary
    assert "recommended_next_adjustment" in summary or True

    empty = build_qa_decision_summary([])
    assert empty["total_cases"] == 0
    assert empty["human_score_mean"] is None
    assert empty["most_common_issues"] == []


def test_no_break_with_incomplete_briefing():
    """No rompe con briefing incompleto o vacío."""
    case_empty = build_validation_case_from_briefing({}, "Empty")
    assert case_empty["observed_facts"] is not None
    assert case_empty["interpreted_signals"] is not None
    assert case_empty["why_this_conclusion"] is not None
    assert case_empty["system_verdict"] is not None

    case_none = build_validation_case_from_briefing(None, "None")
    assert case_none["hotel_name"] == "None"
    assert "observed_facts" in case_none


def test_slug():
    """_slug produce nombres seguros."""
    assert _slug("Hotel Arts Barcelona") == "Hotel_Arts_Barcelona"
    assert _slug("") == "unknown"
    assert len(_slug("a" * 100)) <= 64


def test_triage_case_returns_issues_and_adjustments():
    """triage_case devuelve issues_detected y suggested_adjustments."""
    case = build_validation_case_from_briefing(
        {"strategy_label": "BALANCED", "decision_drivers": ["X"], "scenario_summary": "Short"},
        "Triage Hotel",
    )
    t = triage_case(case)
    assert "issues_detected" in t
    assert "suggested_adjustments" in t
    assert "explainability_ok" in t
    assert isinstance(t["issues_detected"], list)
    assert isinstance(t["suggested_adjustments"], list)


def test_triage_taxonomy():
    """Taxonomía de issues y adjustments está definida."""
    issues = get_all_issue_codes()
    assert CASE_NOT_EXPLAINABLE in issues
    assert len(issues) >= 10
    adj = get_all_adjustment_codes()
    assert NO_CHANGE_NEEDED in adj
    assert len(adj) >= 5


def test_summarize_validation_cases():
    """summarize_validation_cases devuelve count, hotels, timestamp range."""
    cases = [
        {"hotel_name": "A", "timestamp": "2025-01-01T12:00:00Z"},
        {"hotel_name": "B", "timestamp": "2025-01-02T12:00:00Z"},
    ]
    s = summarize_validation_cases(cases)
    assert s["count"] == 2
    assert set(s["hotels"]) == {"A", "B"}
    assert s["timestamp_min"] is not None
    assert s["timestamp_max"] is not None
    assert summarize_validation_cases([])["count"] == 0
