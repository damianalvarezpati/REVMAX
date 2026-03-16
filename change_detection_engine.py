"""
RevMax — Change Detection Engine (Fase 14)
==========================================
Detecta cambios relevantes entre la corrida actual y la anterior usando
el snapshot previo (Intelligence Memory). Comparación semántica para negocio.
No reemplaza la memoria; usa la memoria ya guardada.
"""

from typing import Optional

CHANGE_SEVERITY_LOW = "low"
CHANGE_SEVERITY_MEDIUM = "medium"
CHANGE_SEVERITY_HIGH = "high"


def _safe_str_type(x) -> Optional[str]:
    """Solo tipos hashables para sets; evita unhashable type: 'dict'."""
    if x is None:
        return None
    if isinstance(x, str) and x.strip():
        return x.strip()
    if isinstance(x, (int, float, bool)):
        return str(x)
    return None


def _curr_critical_alert_types(briefing: dict) -> set:
    out = set()
    for a in briefing.get("alerts", []):
        if not isinstance(a, dict):
            continue
        t = _safe_str_type(a.get("type"))
        if t and a.get("severity") == "critical":
            out.add(t)
    return out


def _curr_high_alert_types(briefing: dict) -> set:
    out = set()
    for a in briefing.get("alerts", []):
        if not isinstance(a, dict):
            continue
        t = _safe_str_type(a.get("type"))
        if t and a.get("severity") == "high":
            out.add(t)
    return out


def _curr_top_notification_types(briefing: dict) -> set:
    out = set()
    for n in briefing.get("top_notifications", []):
        if isinstance(n, dict):
            t = _safe_str_type(n.get("type"))
        else:
            t = _safe_str_type(n)
        if t:
            out.add(t)
    return out


def _curr_opportunity_types(briefing: dict) -> set:
    out = set()
    for o in briefing.get("opportunities", []):
        if isinstance(o, dict):
            t = _safe_str_type(o.get("type"))
        else:
            t = _safe_str_type(o)
        if t:
            out.add(t)
    return out


def _curr_action_types(briefing: dict) -> set:
    out = set()
    for a in briefing.get("recommended_actions", []):
        if not isinstance(a, dict):
            continue
        t = _safe_str_type(a.get("type"))
        if t:
            out.add(t)
    return out


def build_change_detection(briefing: dict, previous_snapshot: Optional[dict]) -> dict:
    """
    Compara briefing actual con previous_snapshot (del Intelligence Memory).
    Devuelve change_summary, change_severity, change_highlights y flags de cambio
    (strategy_changed, overall_status_changed, consolidated_action_changed, etc.).
    """
    prev = previous_snapshot or {}
    out = {
        "strategy_changed": briefing.get("strategy_changed", False),
        "overall_status_changed": briefing.get("overall_status_changed", False),
        "consolidated_action_changed": False,
        "top_priority_changed": False,
        "top_value_opportunity_changed": False,
        "recommended_scenario_changed": False,
        "new_critical_alerts": [],
        "resolved_critical_alerts": [],
        "new_high_alerts": [],
        "resolved_high_alerts": [],
        "new_top_notifications": [],
        "resolved_top_notifications": [],
        "opportunity_shift": False,
        "action_shift": briefing.get("action_shift"),
        "scenario_shift": False,
        "change_summary": "",
        "change_severity": CHANGE_SEVERITY_LOW,
        "change_highlights": [],
    }

    if not prev:
        out["change_summary"] = "No previous run to compare; this is the first analysis or no snapshot was found."
        return out

    # Consolidated action
    curr_action = (briefing.get("consolidated_price_action") or "hold").lower()
    prev_action = (prev.get("consolidated_price_action") or "hold").lower()
    out["consolidated_action_changed"] = curr_action != prev_action

    # Top priority item (type)
    top_curr = briefing.get("top_priority_item")
    top_curr_type = top_curr.get("type") if isinstance(top_curr, dict) else None
    top_prev_type = prev.get("top_priority_item_type")
    if top_prev_type is not None and top_curr_type is not None:
        out["top_priority_changed"] = top_curr_type != top_prev_type
    elif top_prev_type is not None or top_curr_type is not None:
        out["top_priority_changed"] = top_curr_type != top_prev_type

    # Top value opportunity (type)
    opp_curr = briefing.get("top_value_opportunity")
    opp_curr_type = opp_curr.get("type") if isinstance(opp_curr, dict) else None
    opp_prev_type = prev.get("top_value_opportunity_type")
    if opp_prev_type is not None and opp_curr_type is not None:
        out["top_value_opportunity_changed"] = opp_curr_type != opp_prev_type
    else:
        out["top_value_opportunity_changed"] = opp_curr_type != opp_prev_type if (opp_prev_type or opp_curr_type) else False

    # Recommended scenario
    curr_scenario = (briefing.get("recommended_scenario") or "hold").lower()
    prev_scenario = (prev.get("recommended_scenario") or "hold").lower()
    out["recommended_scenario_changed"] = curr_scenario != prev_scenario
    out["scenario_shift"] = out["recommended_scenario_changed"]

    # New / resolved critical and high alerts (solo tipos hashables; evita unhashable type: 'dict')
    def _alert_type_list(lst):
        out = set()
        for x in lst or []:
            if isinstance(x, dict):
                t = _safe_str_type(x.get("type"))
            else:
                t = _safe_str_type(x)
            if t:
                out.add(t)
        return out
    new_alert_types = _alert_type_list(briefing.get("new_alerts", []))
    resolved_alert_types = _alert_type_list(briefing.get("resolved_alerts", []))
    curr_critical = _curr_critical_alert_types(briefing)
    curr_high = _curr_high_alert_types(briefing)
    prev_critical = set(prev.get("critical_alert_types") or [])
    prev_high = set(prev.get("high_alert_types") or [])

    out["new_critical_alerts"] = sorted(new_alert_types & curr_critical)
    out["resolved_critical_alerts"] = sorted(resolved_alert_types & prev_critical)
    out["new_high_alerts"] = sorted(new_alert_types & curr_high)
    out["resolved_high_alerts"] = sorted(resolved_alert_types & prev_high)

    # Top notifications
    curr_notif = _curr_top_notification_types(briefing)
    prev_notif = set(prev.get("top_notification_types") or [])
    out["new_top_notifications"] = sorted(curr_notif - prev_notif)
    out["resolved_top_notifications"] = sorted(prev_notif - curr_notif)

    # Opportunity shift (types changed)
    curr_opp_types = _curr_opportunity_types(briefing)
    prev_opp_types = set(prev.get("opportunity_types") or [])
    out["opportunity_shift"] = curr_opp_types != prev_opp_types

    # Severity and summary
    severity = CHANGE_SEVERITY_LOW
    highlights = []

    if out["new_critical_alerts"]:
        severity = CHANGE_SEVERITY_HIGH
        highlights.append(f"New critical alert(s): {', '.join(out['new_critical_alerts'])}.")

    if out["resolved_critical_alerts"]:
        if severity != CHANGE_SEVERITY_HIGH:
            severity = CHANGE_SEVERITY_MEDIUM
        highlights.append(f"Resolved critical alert(s): {', '.join(out['resolved_critical_alerts'])}.")

    if out["strategy_changed"]:
        prev_s = prev.get("strategy_label", "BALANCED")
        curr_s = briefing.get("strategy_label", "BALANCED")
        if severity == CHANGE_SEVERITY_LOW:
            severity = CHANGE_SEVERITY_MEDIUM
        highlights.append(f"Strategy changed from {prev_s} to {curr_s}.")

    if out["overall_status_changed"]:
        prev_st = prev.get("derived_overall_status", "stable")
        curr_st = briefing.get("derived_overall_status", "stable")
        if severity == CHANGE_SEVERITY_LOW:
            severity = CHANGE_SEVERITY_MEDIUM
        highlights.append(f"Overall status changed from {prev_st} to {curr_st}.")

    if out["consolidated_action_changed"] and briefing.get("action_shift"):
        if severity == CHANGE_SEVERITY_LOW:
            severity = CHANGE_SEVERITY_MEDIUM
        highlights.append(f"Consolidated action: {briefing['action_shift']}.")

    if out["recommended_scenario_changed"]:
        if severity == CHANGE_SEVERITY_LOW:
            severity = CHANGE_SEVERITY_MEDIUM
        highlights.append(f"Recommended scenario changed from {prev_scenario} to {curr_scenario}.")

    if out["top_priority_changed"]:
        if severity == CHANGE_SEVERITY_LOW:
            severity = CHANGE_SEVERITY_MEDIUM
        highlights.append("Top priority item changed.")

    if out["new_high_alerts"]:
        if severity == CHANGE_SEVERITY_LOW:
            severity = CHANGE_SEVERITY_MEDIUM
        highlights.append(f"New high-severity alert(s): {', '.join(out['new_high_alerts'])}.")

    out["change_severity"] = severity
    out["change_highlights"] = highlights

    if highlights:
        out["change_summary"] = " ".join(highlights[:3])
        if len(highlights) > 3:
            out["change_summary"] += f" ({len(highlights) - 3} more change(s).)"
    else:
        out["change_summary"] = "No material changes detected since the previous run."

    return out
