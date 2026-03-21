"""Tests: Dojo validation debt inbox and score penalty."""

import json
from pathlib import Path

from dojo_validation_debt import (
    compute_debt_metrics,
    load_inbox,
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
    assert "events" in per


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
