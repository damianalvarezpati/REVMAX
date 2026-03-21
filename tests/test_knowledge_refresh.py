"""Tests: knowledge refresh prioritization, acceptance gate, bootstrap."""

import json
from pathlib import Path

from knowledge_refresh import prioritize_areas, try_accept_observed, load_refresh_config


def _accept_payload(**overrides):
    base = {
        "observed_id": "o1",
        "run_id": "r1",
        "area_key": "demand",
        "source_reference": "ref:MASTER_DATASET_INDEX",
        "knowledge_type": "dataset_signal",
        "reason_for_acceptance": "long enough reason for acceptance",
        "linked_rule_or_hypothesis": "HYP-001",
        "accepted_by": "tester",
        "content_hash": "abc123",
    }
    base.update(overrides)
    return base


def test_prioritize_weak_and_low_score_first():
    areas = [
        {"area_key": "strong_low", "status_label": "strong", "area_score": 5},
        {"area_key": "weak_high", "status_label": "weak", "area_score": 80},
        {"area_key": "weak_low", "status_label": "weak", "area_score": 10},
    ]
    out = prioritize_areas(areas, ["weak", "developing", "usable", "strong"])
    assert [a["area_key"] for a in out] == ["weak_low", "weak_high", "strong_low"]


def test_try_accept_rejects_duplicate_hash(tmp_path: Path):
    rdir = tmp_path / "data/knowledge/refresh"
    rdir.mkdir(parents=True)
    (rdir / "knowledge_refresh_config.json").write_text(
        json.dumps(
            {
                "quality_rules_for_acceptance": {
                    "min_reason_for_acceptance_length": 8,
                    "min_summary_length": 8,
                    "require_area_key": True,
                    "require_content_hash": True,
                }
            }
        ),
        encoding="utf-8",
    )
    base = tmp_path
    ok1, _ = try_accept_observed(base, _accept_payload())
    ok2, msg = try_accept_observed(
        base,
        _accept_payload(observed_id="o2", reason_for_acceptance="another long reason for acceptance"),
    )
    assert ok1 is True
    assert ok2 is False
    assert "duplicado" in msg


def test_try_accept_rejects_short_reason(tmp_path: Path):
    rdir = tmp_path / "data/knowledge/refresh"
    rdir.mkdir(parents=True)
    (rdir / "knowledge_refresh_config.json").write_text(
        json.dumps(
            {
                "quality_rules_for_acceptance": {
                    "min_reason_for_acceptance_length": 20,
                    "require_area_key": True,
                    "require_content_hash": True,
                }
            }
        ),
        encoding="utf-8",
    )
    ok, msg = try_accept_observed(
        tmp_path,
        _accept_payload(reason_for_acceptance="short"),
    )
    assert ok is False
    assert "corto" in msg


def test_try_accept_requires_all_fields(tmp_path: Path):
    rdir = tmp_path / "data/knowledge/refresh"
    rdir.mkdir(parents=True)
    (rdir / "knowledge_refresh_config.json").write_text(
        json.dumps({"quality_rules_for_acceptance": {"require_area_key": True, "require_content_hash": True}}),
        encoding="utf-8",
    )
    ok, msg = try_accept_observed(tmp_path, {"observed_id": "x", "content_hash": "h"})
    assert ok is False
    assert "area_key" in msg or "Falta" in msg


def test_load_refresh_config_missing_returns_empty(tmp_path: Path):
    assert load_refresh_config(tmp_path) == {}
