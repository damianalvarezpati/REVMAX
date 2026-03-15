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
