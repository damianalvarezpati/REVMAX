"""Tests: Dojo validation debt inbox and score penalty."""

import json
from pathlib import Path

from dojo_validation_debt import (
    build_dojo_candidate_linkage,
    compute_debt_metrics,
    load_inbox,
    mark_validation_tasks_done_for_case_path,
    merge_generated_into_inbox,
    sync_validation_inbox,
    update_task_status,
)


def test_merge_and_metrics(tmp_path: Path):
    inbox = {"version": 1, "tasks": [], "updated_at": None}
    gen = [
        {
            "task_id": "t1",
            "task_type": "hypothesis_review",
            "area_key": "events",
            "priority": 9,
            "created_at": "2026-01-01T00:00:00+00:00",
            "reason": "test",
            "linked_hypothesis_id": "X",
            "linked_case_id": None,
            "required_for_area_progress": True,
            "status": "pending",
            "assigned_to": None,
        }
    ]
    merge_generated_into_inbox(inbox, gen)
    assert len(inbox["tasks"]) == 1
    g, per = compute_debt_metrics(inbox, tmp_path)
    assert g["dojo_inbox_count"] == 1
    assert g["pending_hypothesis_reviews"] == 1
    assert g["pending_validation_tasks"] == 0
    assert "events" in per


def test_build_dojo_candidate_linkage_ids():
    rel_obs = [{"observed_id": "obs_x", "ref_path": "data/knowledge/x.json"}]
    rules_by_id = {
        "H1": {"id": "H1", "support": "hypothetical", "applies_to": ["event"]},
        "P1": {"id": "P1", "support": "partial", "applies_to": ["event"]},
    }
    out = build_dojo_candidate_linkage(
        "events",
        rel_obs,
        ["H1", "P1"],
        rules_by_id,
        set(),
        engine_rule_ids_expected=["MISSING"],
    )
    assert out["linked_hypothesis_id"] == "H1"
    assert out["required_review_type"] == "hypothesis_review"
    assert len(out["linked_task_ids"]) >= 3
    assert out["close_condition"]


def test_update_task_status(tmp_path: Path):
    p = tmp_path / "data/dojo"
    p.mkdir(parents=True)
    inbox = {
        "version": 1,
        "tasks": [
            {
                "task_id": "x1",
                "task_type": "validation_case",
                "area_key": "demand",
                "priority": 5,
                "created_at": "2026-01-01T00:00:00+00:00",
                "reason": "r",
                "linked_case_id": None,
                "required_for_area_progress": True,
                "status": "pending",
                "assigned_to": None,
            }
        ],
    }
    (tmp_path / "data/dojo/validation_inbox.json").write_text(json.dumps(inbox), encoding="utf-8")
    ok, msg = update_task_status(tmp_path, "x1", "done")
    assert ok
    data = json.loads((tmp_path / "data/dojo/validation_inbox.json").read_text(encoding="utf-8"))
    assert data["tasks"][0]["status"] == "done"


def test_sync_creates_tasks_from_rules(tmp_path: Path):
    (tmp_path / "data/knowledge").mkdir(parents=True)
    (tmp_path / "data/dojo").mkdir(parents=True)
    (tmp_path / "data/knowledge/knowledge_areas_config.json").write_text(
        json.dumps(
            {
                "areas": [
                    {
                        "area_key": "events",
                        "area_name": "E",
                        "rule_applies_to_substrings": ["event"],
                        "engine_rule_ids": [],
                        "pattern_files": [],
                    }
                ],
                "engine_integrated_rule_ids": [],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "data/knowledge/candidate_rules.json").write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "id": "TST-HYP",
                        "support": "hypothetical",
                        "applies_to": ["event_pressure", "dojo"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "data/dojo/validation_inbox.json").write_text(
        json.dumps({"version": 1, "tasks": []}),
        encoding="utf-8",
    )
    (tmp_path / "data/dojo/validation_debt_config.json").write_text(
        json.dumps(
            {
                "block_if_required_pending": 99,
                "block_validation_debt_score": 99,
            }
        ),
        encoding="utf-8",
    )
    sync_validation_inbox(tmp_path)
    data = load_inbox(tmp_path)
    assert any(t.get("task_type") == "hypothesis_review" for t in data.get("tasks", []))


def test_mark_validation_tasks_done_matches_path(tmp_path: Path):
    case_path = str(tmp_path / "data/qa_runs/case1.json")
    p = tmp_path / "data/dojo"
    p.mkdir(parents=True)
    (tmp_path / "data/qa_runs").mkdir(parents=True)
    Path(case_path).write_text("{}", encoding="utf-8")
    inbox = {
        "version": 1,
        "tasks": [
            {
                "task_id": "qa_x",
                "task_type": "validation_case",
                "area_key": "demand",
                "priority": 5,
                "created_at": "2026-01-01T00:00:00+00:00",
                "reason": "r",
                "linked_case_id": case_path,
                "required_for_area_progress": True,
                "status": "pending",
                "assigned_to": None,
            }
        ],
    }
    (tmp_path / "data/dojo/validation_inbox.json").write_text(json.dumps(inbox), encoding="utf-8")
    n = mark_validation_tasks_done_for_case_path(tmp_path, case_path)
    assert n == 1
    data = json.loads((tmp_path / "data/dojo/validation_inbox.json").read_text(encoding="utf-8"))
    assert data["tasks"][0]["status"] == "done"
    assert data["tasks"][0].get("closure_quality") == "resolved"


def _write_min_debt_cfg(p: Path) -> None:
    (p / "data/dojo").mkdir(parents=True, exist_ok=True)
    (p / "data/dojo/validation_debt_config.json").write_text(
        json.dumps(
            {
                "block_if_required_pending": 99,
                "block_validation_debt_score": 99,
                "dismissed_residual_with_reason": 0.2,
                "dismissed_residual_without_reason": 0.5,
                "honest_closure_dismiss_weight": 0.5,
                "task_weights": {"hypothesis_review": 1.0},
            }
        ),
        encoding="utf-8",
    )


def test_done_clears_pending_debt_not_dismissed(tmp_path: Path):
    _write_min_debt_cfg(tmp_path)
    tid = "t_hyp"
    inbox = {
        "version": 1,
        "tasks": [
            {
                "task_id": tid,
                "task_type": "hypothesis_review",
                "area_key": "events",
                "priority": 10,
                "created_at": "2026-01-01T00:00:00+00:00",
                "reason": "r",
                "linked_hypothesis_id": "X",
                "linked_case_id": None,
                "required_for_area_progress": True,
                "status": "pending",
                "assigned_to": None,
            }
        ],
    }
    (tmp_path / "data/dojo/validation_inbox.json").write_text(json.dumps(inbox), encoding="utf-8")
    g0, per0 = compute_debt_metrics(inbox, tmp_path)
    assert per0["events"]["pending_debt_score"] > 0
    assert per0["events"]["dismissal_residual_debt_score"] == 0

    update_task_status(tmp_path, tid, "done", closed_by="t", closure_source="test")
    inbox2 = load_inbox(tmp_path)
    g1, per1 = compute_debt_metrics(inbox2, tmp_path)
    assert per1["events"]["pending_debt_score"] == 0
    assert per1["events"]["effective_validation_debt"] == 0
    assert per1["events"]["honest_validation_closure_score"] == 100.0


def test_dismissed_retains_residual_debt_less_than_pending(tmp_path: Path):
    _write_min_debt_cfg(tmp_path)
    tid = "t_hyp2"
    inbox = {
        "version": 1,
        "tasks": [
            {
                "task_id": tid,
                "task_type": "hypothesis_review",
                "area_key": "events",
                "priority": 10,
                "created_at": "2026-01-01T00:00:00+00:00",
                "reason": "r",
                "linked_hypothesis_id": "X",
                "linked_case_id": None,
                "required_for_area_progress": True,
                "status": "pending",
                "assigned_to": None,
            }
        ],
    }
    (tmp_path / "data/dojo/validation_inbox.json").write_text(json.dumps(inbox), encoding="utf-8")
    g0, per0 = compute_debt_metrics(inbox, tmp_path)
    pending_eff = per0["events"]["effective_validation_debt"]

    update_task_status(tmp_path, tid, "dismissed", dismiss_reason="explained")
    inbox_d = load_inbox(tmp_path)
    g1, per1 = compute_debt_metrics(inbox_d, tmp_path)
    assert per1["events"]["pending_debt_score"] == 0
    assert per1["events"]["dismissal_residual_debt_score"] > 0
    assert per1["events"]["effective_validation_debt"] < pending_eff
    assert per1["events"]["effective_validation_debt"] > 0
    assert per1["events"]["honest_validation_closure_score"] == 0.0
    t = inbox_d["tasks"][0]
    assert t.get("closure_quality") == "dismissed_with_reason"
    assert g1["debt_dismissed_count"] == 1
    assert g1["debt_resolved_count"] == 0


def test_mass_dismiss_does_not_yield_honest_maturity(tmp_path: Path):
    _write_min_debt_cfg(tmp_path)
    tasks = []
    for i in range(4):
        tasks.append(
            {
                "task_id": f"d{i}",
                "task_type": "hypothesis_review",
                "area_key": "events",
                "priority": 8,
                "created_at": "2026-01-01T00:00:00+00:00",
                "reason": "r",
                "required_for_area_progress": False,
                "status": "dismissed",
                "dismiss_reason": "",
                "close_reason": None,
            }
        )
    inbox = {"version": 1, "tasks": tasks}
    (tmp_path / "data/dojo/validation_inbox.json").write_text(json.dumps(inbox), encoding="utf-8")
    g, per = compute_debt_metrics(inbox, tmp_path)
    assert per["events"]["honest_validation_closure_score"] == 0.0
    # Deuda efectiva sigue alta: dismiss no vacía el score como un done honesto.
    assert per["events"]["effective_validation_debt"] > 5
