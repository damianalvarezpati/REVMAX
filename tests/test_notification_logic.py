"""
Tests unitarios de Notification Logic (Fase 7).
Ejecutar desde la raíz: pytest tests/test_notification_logic.py -v
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from notification_logic import (
    build_notification_bundle,
    MAX_TOP_NOTIFICATIONS,
    NOTIFICATION_PRIORITIES,
    DELIVERY_INTENTS,
)


def _briefing(alerts=None, market_signals=None, recommended_actions=None, derived_overall_status="stable", strategy_label="BALANCED"):
    return {
        "alerts": alerts or [],
        "market_signals": market_signals or [],
        "recommended_actions": recommended_actions or [],
        "derived_overall_status": derived_overall_status,
        "strategy_label": strategy_label,
    }


def _action(type_, priority="medium", horizon="this_week", title="", rationale="", source_signals=None, expected_effect=""):
    return {
        "type": type_,
        "priority": priority,
        "horizon": horizon,
        "title": title or type_,
        "rationale": rationale,
        "source_signals": source_signals or [],
        "expected_effect": expected_effect,
    }


# 1. Parity critical + FIX_PARITY urgent => urgent notification
def test_parity_critical_fix_parity_urgent_notification():
    """Paridad crítica y acción FIX_PARITY urgente deben generar notificación urgente CRITICAL_PARITY_NOTIFICATION."""
    briefing = _briefing(
        alerts=[{"type": "PARITY_VIOLATION", "severity": "critical", "message": "Parity", "source": "distribution"}],
        recommended_actions=[_action("FIX_PARITY", priority="urgent", horizon="immediate", source_signals=["PARITY_VIOLATION"])],
    )
    bundle = build_notification_bundle(briefing)
    top = bundle["top_notifications"]
    types = [n["type"] for n in top]
    assert "CRITICAL_PARITY_NOTIFICATION" in types
    notif = next(n for n in top if n["type"] == "CRITICAL_PARITY_NOTIFICATION")
    assert notif["priority"] == "urgent"
    assert notif["delivery_intent"] == "immediate_attention"
    assert "PARITY_VIOLATION" in notif["source_items"] and "FIX_PARITY" in notif["source_items"]
    assert bundle["notification_priority_counts"].get("urgent", 0) >= 1


# 2. Weak demand + monitor action => medium/low notification
def test_weak_demand_monitor_action_medium_notification():
    """Demanda débil y acción MONITOR_DEMAND deben generar DEMAND_RISK_NOTIFICATION con prioridad medium o high."""
    briefing = _briefing(
        market_signals=[{"type": "WEAK_DEMAND_REQUIRES_CAUTION", "strength": "medium", "directional_effect": "caution", "source": "demand", "message": "Weak"}],
        recommended_actions=[_action("MONITOR_DEMAND", priority="medium", source_signals=["WEAK_DEMAND_REQUIRES_CAUTION"])],
    )
    bundle = build_notification_bundle(briefing)
    top = bundle["top_notifications"]
    types = [n["type"] for n in top]
    assert "DEMAND_RISK_NOTIFICATION" in types
    notif = next(n for n in top if n["type"] == "DEMAND_RISK_NOTIFICATION")
    assert notif["priority"] in ("medium", "high")
    assert "summary" in notif and "rationale" in notif and "source_items" in notif


# 3. Underpriced + increase action => high notification
def test_underpriced_increase_action_high_notification():
    """Underpriced y acción PRICE_INCREASE deben generar notificación alta (PRICE_OPPORTUNITY o UNDERVALUATION)."""
    briefing = _briefing(
        market_signals=[
            {"type": "UNDERPRICED_RELATIVE_TO_POSITION", "strength": "high", "directional_effect": "raise", "source": "reputation", "message": "Underpriced"},
            {"type": "DEMAND_SUPPORTS_INCREASE", "strength": "medium", "directional_effect": "raise", "source": "demand", "message": "Demand supports"},
        ],
        recommended_actions=[_action("PRICE_INCREASE", priority="high", source_signals=["UNDERPRICED_RELATIVE_TO_POSITION", "DEMAND_SUPPORTS_INCREASE"])],
    )
    bundle = build_notification_bundle(briefing)
    top = bundle["top_notifications"]
    types = [n["type"] for n in top]
    assert "PRICE_OPPORTUNITY_NOTIFICATION" in types or "UNDERVALUATION_OPPORTUNITY_NOTIFICATION" in types
    high_notifs = [n for n in top if n["priority"] == "high"]
    assert len(high_notifs) >= 1


# 4. Low visibility + improve visibility => high/medium notification
def test_low_visibility_improve_visibility_notification():
    """LOW_VISIBILITY y acción IMPROVE_VISIBILITY deben generar VISIBILITY_ISSUE_NOTIFICATION."""
    briefing = _briefing(
        alerts=[{"type": "LOW_VISIBILITY", "severity": "warning", "message": "Low vis", "source": "distribution"}],
        recommended_actions=[_action("IMPROVE_VISIBILITY", priority="high", source_signals=["LOW_VISIBILITY"])],
    )
    bundle = build_notification_bundle(briefing)
    top = bundle["top_notifications"]
    types = [n["type"] for n in top]
    assert "VISIBILITY_ISSUE_NOTIFICATION" in types
    notif = next(n for n in top if n["type"] == "VISIBILITY_ISSUE_NOTIFICATION")
    assert notif["priority"] in ("high", "medium")
    assert "LOW_VISIBILITY" in notif["source_items"]


# 5. Defensive strategy + critical alerts => defensive notification
def test_defensive_strategy_critical_alerts_defensive_notification():
    """Estrategia DEFENSIVE con alertas críticas debe generar DEFENSIVE_POSTURE_NOTIFICATION."""
    briefing = _briefing(
        strategy_label="DEFENSIVE",
        derived_overall_status="alert",
        alerts=[{"type": "PARITY_VIOLATION", "severity": "critical", "message": "P", "source": "d"}],
        recommended_actions=[_action("FIX_PARITY", priority="urgent", source_signals=["PARITY_VIOLATION"])],
    )
    bundle = build_notification_bundle(briefing)
    top = bundle["top_notifications"]
    types = [n["type"] for n in top]
    assert "DEFENSIVE_POSTURE_NOTIFICATION" in types
    notif = next(n for n in top if n["type"] == "DEFENSIVE_POSTURE_NOTIFICATION")
    assert notif["priority"] in ("urgent", "high")
    assert "strategy_DEFENSIVE" in notif["source_items"]


# 6. Deduplication and max 5 top_notifications
def test_deduplication_max_five_top_notifications():
    """Máximo 5 top_notifications; deduplicación por tipo (mayor prioridad gana)."""
    briefing = _briefing(
        alerts=[
            {"type": "PARITY_VIOLATION", "severity": "critical", "message": "P", "source": "d"},
            {"type": "LOW_VISIBILITY", "severity": "warning", "message": "V", "source": "d"},
            {"type": "DEMAND_COLLAPSE", "severity": "high", "message": "D", "source": "d"},
        ],
        market_signals=[
            {"type": "DEMAND_SUPPORTS_INCREASE", "strength": "high", "directional_effect": "raise", "source": "demand", "message": "M"},
            {"type": "UNDERPRICED_RELATIVE_TO_POSITION", "strength": "medium", "directional_effect": "raise", "source": "rep", "message": "U"},
            {"type": "WEAK_DEMAND_REQUIRES_CAUTION", "strength": "medium", "directional_effect": "caution", "source": "demand", "message": "W"},
        ],
        recommended_actions=[
            _action("FIX_PARITY", priority="urgent", source_signals=["PARITY_VIOLATION"]),
            _action("IMPROVE_VISIBILITY", priority="high", source_signals=["LOW_VISIBILITY"]),
            _action("MONITOR_DEMAND", priority="medium", source_signals=["WEAK_DEMAND_REQUIRES_CAUTION"]),
            _action("PRICE_INCREASE", priority="high", source_signals=["DEMAND_SUPPORTS_INCREASE"]),
            _action("REVIEW_POSITIONING", priority="medium", source_signals=["UNDERPRICED_RELATIVE_TO_POSITION"]),
        ],
        strategy_label="DEFENSIVE",
        derived_overall_status="alert",
    )
    bundle = build_notification_bundle(briefing)
    top = bundle["top_notifications"]
    assert len(top) <= MAX_TOP_NOTIFICATIONS
    types_seen = []
    for n in top:
        assert n["type"] not in types_seen
        types_seen.append(n["type"])
    assert "notification_candidates" in bundle
    assert "notification_summary" in bundle
    assert "notification_priority_counts" in bundle
    assert set(bundle["notification_priority_counts"].keys()) >= {"urgent", "high", "medium", "low"}
    for n in top:
        assert n.get("type") and n.get("priority") and n.get("title") and n.get("summary")
        assert n.get("rationale") is not None and n.get("source_items") is not None
        assert n.get("delivery_intent") in DELIVERY_INTENTS
        assert n.get("priority") in NOTIFICATION_PRIORITIES


def test_empty_briefing_no_crash():
    """Briefing sin alertas ni acciones no debe romper; bundle con listas vacías o mínimas."""
    bundle = build_notification_bundle(_briefing())
    assert "top_notifications" in bundle
    assert "notification_candidates" in bundle
    assert "notification_summary" in bundle
    assert "notification_priority_counts" in bundle
    assert isinstance(bundle["top_notifications"], list)
    assert isinstance(bundle["notification_priority_counts"], dict)
