"""Tests: knowledge refresh prioritization, acceptance gate, bootstrap."""

import json
from pathlib import Path

from knowledge_refresh import prioritize_areas, try_accept_observed, load_refresh_config


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
                    "min_summary_length": 8,
                    "require_area_key": True,
                    "require_content_hash": True,
                }
            }
        ),
        encoding="utf-8",
    )
    base = tmp_path
    ok1, _ = try_accept_observed(
        base,
        observed_id="o1",
        run_id="r1",
        summary="long enough summary",
        area_key="demand",
        content_hash="abc123",
    )
    ok2, msg = try_accept_observed(
        base,
        observed_id="o2",
        run_id="r1",
        summary="another long summary",
        area_key="demand",
        content_hash="abc123",
    )
    assert ok1 is True
    assert ok2 is False
    assert "duplicado" in msg


def test_try_accept_rejects_short_summary(tmp_path: Path):
    rdir = tmp_path / "data/knowledge/refresh"
    rdir.mkdir(parents=True)
    (rdir / "knowledge_refresh_config.json").write_text(
        json.dumps(
            {
                "quality_rules_for_acceptance": {
                    "min_summary_length": 20,
                    "require_area_key": True,
                    "require_content_hash": True,
                }
            }
        ),
        encoding="utf-8",
    )
    ok, msg = try_accept_observed(
        tmp_path,
        observed_id="x",
        run_id=None,
        summary="short",
        area_key="demand",
        content_hash="h1",
    )
    assert ok is False
    assert "corto" in msg


def test_load_refresh_config_missing_returns_empty(tmp_path: Path):
    assert load_refresh_config(tmp_path) == {}
