"""Tests: knowledge balancing engine — shares, modes, refresh selection."""

from knowledge_balancing_engine import (
    enrich_areas_with_knowledge_balance,
    select_areas_for_refresh,
    dojo_candidate_multiplier_for_area,
)


def test_enrich_adds_knowledge_balance_and_shares_sum():
    areas = [
        {
            "area_key": "a_weak",
            "area_name": "Weak",
            "area_score": 22.0,
            "status_label": "weak",
            "validation_score": 30.0,
            "coverage_score": 40.0,
            "model_readiness_score": 20.0,
            "missing_gaps": [],
            "suggested_actions": [],
        },
        {
            "area_key": "b_strong",
            "area_name": "Strong",
            "area_score": 88.0,
            "status_label": "strong",
            "validation_score": 90.0,
            "coverage_score": 85.0,
            "model_readiness_score": 80.0,
            "missing_gaps": [],
            "suggested_actions": [],
        },
    ]
    enriched, summary = enrich_areas_with_knowledge_balance(areas, base_dir=None)
    assert len(enriched) == 2
    shares = [e["knowledge_balance"]["recommended_effort_share"] for e in enriched]
    assert abs(sum(shares) - 1.0) < 0.02
    assert "total_effort_share_check" in summary
    weak = next(e for e in enriched if e["area_key"] == "a_weak")
    strong = next(e for e in enriched if e["area_key"] == "b_strong")
    assert weak["knowledge_balance"]["knowledge_gap_score"] > strong["knowledge_balance"]["knowledge_gap_score"]
    assert weak["knowledge_balance"]["recommended_effort_share"] > strong["knowledge_balance"]["recommended_effort_share"]


def test_select_areas_prefers_high_gap():
    areas = [
        {"area_key": "x", "knowledge_balance": {"growth_priority": 20.0, "knowledge_gap_score": 10.0}},
        {"area_key": "y", "knowledge_balance": {"growth_priority": 80.0, "knowledge_gap_score": 40.0}},
        {"area_key": "z", "knowledge_balance": {"growth_priority": 50.0, "knowledge_gap_score": 25.0}},
    ]
    chosen, meta = select_areas_for_refresh(areas, 2, prefer_balance=True)
    assert chosen[0] == "y"
    assert meta["policy"] == "knowledge_balance_priority"


def test_dojo_multiplier_maintenance_is_one():
    area = {
        "area_key": "p",
        "knowledge_balance": {
            "mode": "maintenance",
            "knowledge_gap_score": 2.0,
            "recommended_effort_share": 0.1,
        },
    }
    m = dojo_candidate_multiplier_for_area(area, {"dojo_effort_multiplier_max": 2.5}, 9)
    assert m == 1.0
