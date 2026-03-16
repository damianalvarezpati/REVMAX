"""
RevMax — Tests de humo para el Report Agent robusto.
Comprueban: JSON válido, texto+JSON, JSON roto, truncado, fallback mínimo, HTML desde fallback.
"""

import json
import pytest

from agents.agent_07_report import (
    _parse_report_response,
    _build_minimal_report_from_analysis,
    _normalize_report_dict,
    _build_report_prompt,
    _normalize_list_of_strings,
    _normalize_list_of_dicts,
)


def _full_analysis(hotel_name="Hotel Test"):
    return {
        "hotel_name": hotel_name,
        "analysis_date": "2025-03-14",
        "briefing": {
            "derived_overall_status": "stable",
            "consolidated_price_action": "hold",
            "recommended_priority_actions_seed": [
                {"urgency": "this_week", "reason_source": "consolidation", "action_hint": "Mantener hold."},
            ],
        },
        "agent_outputs": {},
    }


def test_valid_json_parsed():
    raw = json.dumps({
        "email_subject": "RevMax · Hotel Test · 14 Mar",
        "overall_status": "stable",
        "status_summary": "Todo estable.",
        "report_text": "Resumen ejecutivo.\n\nPostura hold.",
        "priority_actions": [
            {"rank": 1, "urgency": "this_week", "action": "Mantener precio", "reason": "Pricing", "expected_impact": ""},
        ],
        "weekly_watchlist": "Vigilar demanda.",
    }, ensure_ascii=False)
    result, used_fallback = _parse_report_response(raw, _full_analysis())
    assert used_fallback is False
    assert result["email_subject"] == "RevMax · Hotel Test · 14 Mar"
    assert result["overall_status"] == "stable"
    assert "report_text" in result and len(result["report_text"]) > 0
    assert isinstance(result["priority_actions"], list)
    assert result.get("weekly_watchlist") == "Vigilar demanda."


def test_text_plus_json_parsed():
    raw = "Aquí tienes el informe:\n\n" + json.dumps({
        "email_subject": "Asunto",
        "overall_status": "stable",
        "status_summary": "Ok",
        "report_text": "Cuerpo del informe.",
        "priority_actions": [],
        "weekly_watchlist": "Nada.",
    }, ensure_ascii=False) + "\n\nFin."
    result, used_fallback = _parse_report_response(raw, _full_analysis())
    assert used_fallback is False
    assert result["report_text"] == "Cuerpo del informe."
    assert result["email_subject"] == "Asunto"


def test_broken_json_fallback():
    raw = '{"email_subject": "x", "overall_status": "stable", "report_text": "ok"'
    result, used_fallback = _parse_report_response(raw, _full_analysis())
    assert used_fallback is True
    assert isinstance(result, dict)
    assert result.get("email_subject")
    assert result.get("report_text")
    assert result.get("priority_actions") is not None
    assert result.get("weekly_watchlist") is not None
    assert result.get("status_summary") is not None


def test_truncated_response_fallback():
    raw = '{"email_subject": "RevMax", "overall_status": "stable", "status_summary": "x", "report_text": "Incomplete'
    result, used_fallback = _parse_report_response(raw, _full_analysis())
    assert used_fallback is True
    assert result.get("report_text")
    assert result.get("priority_actions") is not None


def test_invalid_json_no_object_fallback():
    raw = "[1, 2, 3]"
    result, used_fallback = _parse_report_response(raw, _full_analysis())
    assert used_fallback is True
    assert result.get("email_subject")
    assert result.get("report_text")


def test_empty_response_fallback():
    result, used_fallback = _parse_report_response("", _full_analysis())
    assert used_fallback is True
    assert result.get("email_subject")
    assert result.get("report_text")


def test_minimal_fallback_has_required_keys():
    minimal = _build_minimal_report_from_analysis(_full_analysis())
    required = ["email_subject", "overall_status", "status_summary", "report_text", "priority_actions", "weekly_watchlist"]
    for k in required:
        assert k in minimal, f"missing key: {k}"
    assert isinstance(minimal["priority_actions"], list)
    assert len(minimal["priority_actions"]) >= 1
    assert isinstance(minimal["report_text"], str)
    assert isinstance(minimal["weekly_watchlist"], str)


def test_normalize_report_dict_fills_missing():
    full = _full_analysis("N")
    incomplete = {"email_subject": "X", "overall_status": "stable", "report_text": "Texto"}
    out = _normalize_report_dict(incomplete, full)
    assert out.get("status_summary") is not None
    assert out.get("weekly_watchlist") is not None
    assert isinstance(out.get("priority_actions"), list)


def test_html_built_from_fallback():
    from mailer.report_mailer_v2 import build_email_html_v2
    full = _full_analysis("Hotel Fallback")
    report = _build_minimal_report_from_analysis(full)
    html = build_email_html_v2(full, report)
    assert isinstance(html, str)
    assert len(html) > 200
    assert "Hotel Fallback" in html
    assert "<!DOCTYPE html" in html or "<html" in html
    assert "</body>" in html


# --- Tests para bug "unhashable type: 'dict'" (listas mixtas en briefing) ---


def test_normalize_list_of_strings_mixed():
    """Lista con strings y dicts no debe romper."""
    out = _normalize_list_of_strings(["a", {"x": 1}, None, "b"], max_len=80)
    assert out == ["a", '{"x": 1}', "b"]
    out2 = _normalize_list_of_strings([], max_len=80)
    assert out2 == []


def test_normalize_list_of_dicts_skips_non_dict():
    """Solo dicts; strings/otros se ignoran."""
    out = _normalize_list_of_dicts([{"type": "A", "title": "T1"}, "string", {"type": "B"}], ["type", "title"])
    assert len(out) == 2
    assert out[0]["type"] == "A" and out[0]["title"] == "T1"
    assert out[1]["type"] == "B"


def test_build_report_prompt_opportunities_mixed_strings_dicts():
    """Briefing con opportunities mezclando strings y dicts no debe lanzar unhashable."""
    full = _full_analysis("Hotel Mixed")
    full["briefing"]["opportunities"] = [
        {"type": "PRICE_CAPTURE", "opportunity_level": "high", "title": "O1", "summary": "S1"},
        "a string opportunity",
    ]
    full["briefing"]["executive_summary_seed"] = ["Line 1", "Line 2", {"bad": "dict"}, "Line 4"]
    full["briefing"]["executive_top_risks"] = [{"type": "ALERT", "severity": "high", "message": "M"}]
    full["briefing"]["executive_top_actions"] = [{"type": "ACTION", "title": "Do X"}]
    full["briefing"]["executive_top_opportunities"] = [{"type": "OPP", "title": "Y"}]
    full["agent_outputs"] = {
        "discovery": {"adr_double": 150},
        "compset": {"compset_summary": {"primary_avg_adr": 140}},
        "pricing": {"market_context": {"your_position_rank": 1, "total_compset": 5}, "indices": {"ari": {"value": 1.0}, "rgi": {"value": 1.0}}, "position_diagnosis": {"quadrant": "?"}, "recommendation": {"action": "hold"}},
        "demand": {"demand_index": {"score": 50, "signal": "medium"}, "events_detected": []},
        "reputation": {"gri": {"value": 7}},
        "distribution": {"visibility_score": 0.8, "rate_parity": {"status": "ok"}, "booking_audit": {"search_position": 1}},
    }
    prompt = _build_report_prompt(full)
    assert isinstance(prompt, str)
    assert "Hotel Mixed" in prompt
    assert "unhashable" not in prompt.lower()
    assert len(prompt) > 500


def test_build_report_prompt_top_notifications_and_scenario_dicts():
    """Briefing con top_notifications y scenario_assessment como listas de dicts."""
    full = _full_analysis("Hotel Notif")
    full["briefing"]["top_notifications"] = [{"type": "N1", "priority": "high"}, {"type": "N2"}]
    full["briefing"]["scenario_assessment"] = [{"scenario": "raise", "net_score": 1}]
    full["briefing"]["decision_drivers"] = ["D1", {"key": "val"}]  # mixed
    full["agent_outputs"] = {
        "discovery": {"adr_double": 100},
        "compset": {"compset_summary": {"primary_avg_adr": 100}},
        "pricing": {"market_context": {"your_position_rank": 1, "total_compset": 5}, "indices": {"ari": {"value": 1}, "rgi": {"value": 1}}, "position_diagnosis": {"quadrant": "?"}, "recommendation": {"action": "hold"}},
        "demand": {"demand_index": {"score": 50, "signal": "medium"}, "events_detected": []},
        "reputation": {"gri": {"value": 7}},
        "distribution": {"visibility_score": 0.8, "rate_parity": {"status": "ok"}, "booking_audit": {"search_position": 1}},
    }
    prompt = _build_report_prompt(full)
    assert isinstance(prompt, str)
    assert "Hotel Notif" in prompt
    assert len(prompt) > 300


def test_build_report_prompt_seed_with_dict_item_no_exception():
    """executive_summary_seed con un item dict no debe lanzar unhashable al formatear."""
    full = _full_analysis("Hotel Seed")
    full["briefing"]["executive_summary_seed"] = ["L1", {"type": "x"}, "L3", "L4"]
    full["agent_outputs"] = {
        "discovery": {"adr_double": 100},
        "compset": {"compset_summary": {"primary_avg_adr": 100}},
        "pricing": {"market_context": {"your_position_rank": 1, "total_compset": 5}, "indices": {"ari": {"value": 1}, "rgi": {"value": 1}}, "position_diagnosis": {}, "recommendation": {"action": "hold"}},
        "demand": {"demand_index": {"score": 50, "signal": "medium"}, "events_detected": []},
        "reputation": {"gri": {"value": 7}},
        "distribution": {"visibility_score": 0.8, "rate_parity": {"status": "ok"}, "booking_audit": {}},
    }
    prompt = _build_report_prompt(full)
    assert isinstance(prompt, str)
    assert "Hotel Seed" in prompt
    assert "Resumen semilla" in prompt
