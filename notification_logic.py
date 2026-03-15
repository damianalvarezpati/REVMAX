"""
RevMax — Notification / Delivery Logic (Fase 7)
================================================
Determina qué hallazgos son comunicables, con qué prioridad y formato.
Generado por código, no por LLM. No envía nada; solo produce el bundle.
"""

NOTIFICATION_PRIORITIES = ("low", "medium", "high", "urgent")
DELIVERY_INTENTS = ("immediate_attention", "include_in_report", "monitor_only")
MAX_TOP_NOTIFICATIONS = 5

PRIORITY_ORDER = {"urgent": 4, "high": 3, "medium": 2, "low": 1}


def _notification(
    type_: str,
    priority: str,
    title: str,
    summary: str,
    rationale: str,
    source_items: list,
    delivery_intent: str,
) -> dict:
    return {
        "type": type_,
        "priority": priority,
        "title": title,
        "summary": summary,
        "rationale": rationale,
        "source_items": source_items,
        "delivery_intent": delivery_intent,
    }


def build_notification_bundle(briefing: dict) -> dict:
    """
    Lee alerts, market_signals, recommended_actions, derived_overall_status y strategy_label
    del briefing; produce notification_candidates, top_notifications, notification_summary
    y notification_priority_counts. Deduplicado por tipo (mayor prioridad gana); máximo 5 top.
    """
    alerts = briefing.get("alerts", [])
    market_signals = briefing.get("market_signals", [])
    recommended_actions = briefing.get("recommended_actions", [])
    derived_status = briefing.get("derived_overall_status", "stable")
    strategy_label = briefing.get("strategy_label", "BALANCED")

    alert_types = {a.get("type") for a in alerts}
    action_types = {a.get("type") for a in recommended_actions}
    signal_types = {s.get("type") for s in market_signals}
    has_critical = any(a.get("severity") == "critical" for a in alerts)
    has_high_alert = any(a.get("severity") == "high" for a in alerts)
    has_urgent_action = any(a.get("priority") == "urgent" for a in recommended_actions)
    has_high_action = any(a.get("priority") == "high" for a in recommended_actions)

    candidates = []

    # 1. CRITICAL_PARITY_NOTIFICATION — parity critical + FIX_PARITY urgent
    if "PARITY_VIOLATION" in alert_types and "FIX_PARITY" in action_types:
        candidates.append(_notification(
            "CRITICAL_PARITY_NOTIFICATION",
            "urgent",
            "Parity issue requires immediate attention",
            "Rate parity violation detected across channels.",
            "Critical alert and action FIX_PARITY both point to immediate intervention.",
            ["PARITY_VIOLATION", "FIX_PARITY"],
            "immediate_attention",
        ))

    # 2. DEFENSIVE_POSTURE_NOTIFICATION — defensive + critical/high alerts
    if strategy_label == "DEFENSIVE" and (has_critical or has_high_alert or derived_status == "alert"):
        priority = "urgent" if has_critical else "high"
        candidates.append(_notification(
            "DEFENSIVE_POSTURE_NOTIFICATION",
            priority,
            "Defensive posture with active alerts",
            "Strategy is DEFENSIVE and there are critical or high-severity alerts; avoid risky price moves.",
            "Alerts and defensive strategy both indicate stabilising position before any aggressive action.",
            ["strategy_DEFENSIVE", "alerts_critical_or_high"],
            "immediate_attention" if has_critical else "include_in_report",
        ))

    # 3. DEMAND_RISK_NOTIFICATION — weak demand / collapse + monitor or hold action
    if "DEMAND_COLLAPSE" in alert_types or "WEAK_DEMAND_REQUIRES_CAUTION" in signal_types:
        sources = []
        if "DEMAND_COLLAPSE" in alert_types:
            sources.append("DEMAND_COLLAPSE")
        if "WEAK_DEMAND_REQUIRES_CAUTION" in signal_types:
            sources.append("WEAK_DEMAND_REQUIRES_CAUTION")
        if "MONITOR_DEMAND" in action_types:
            sources.append("MONITOR_DEMAND")
        if "HOLD_PRICE" in action_types:
            sources.append("HOLD_PRICE")
        if not sources:
            sources = ["DEMAND_COLLAPSE"] if "DEMAND_COLLAPSE" in alert_types else ["WEAK_DEMAND_REQUIRES_CAUTION"]
        priority = "high" if "DEMAND_COLLAPSE" in alert_types else "medium"
        candidates.append(_notification(
            "DEMAND_RISK_NOTIFICATION",
            priority,
            "Demand risk requires caution",
            "Demand is weak or collapsed; do not raise prices; monitor and hold recommended.",
            "Alert or market signal and recommended actions align on caution.",
            sources,
            "include_in_report" if priority == "high" else "monitor_only",
        ))

    # 4. PRICE_OPPORTUNITY_NOTIFICATION — raise action + demand/reputation signals
    if "PRICE_INCREASE" in action_types and (
        "DEMAND_SUPPORTS_INCREASE" in signal_types or "COMPETITOR_PRICE_PRESSURE" in signal_types
    ):
        sources = ["PRICE_INCREASE"]
        if "DEMAND_SUPPORTS_INCREASE" in signal_types:
            sources.append("DEMAND_SUPPORTS_INCREASE")
        if "COMPETITOR_PRICE_PRESSURE" in signal_types:
            sources.append("COMPETITOR_PRICE_PRESSURE")
        candidates.append(_notification(
            "PRICE_OPPORTUNITY_NOTIFICATION",
            "high",
            "Price increase opportunity",
            "Consolidation and market signals support a price increase; demand or competition supports capture.",
            "Recommended action PRICE_INCREASE aligned with strong market signals.",
            sources,
            "include_in_report",
        ))

    # 5. UNDERVALUATION_OPPORTUNITY_NOTIFICATION — underpriced + increase or review
    if "UNDERPRICED_RELATIVE_TO_POSITION" in signal_types and (
        "PRICE_INCREASE" in action_types or "REVIEW_POSITIONING" in action_types
    ):
        sources = ["UNDERPRICED_RELATIVE_TO_POSITION"]
        if "PRICE_INCREASE" in action_types:
            sources.append("PRICE_INCREASE")
        if "REVIEW_POSITIONING" in action_types:
            sources.append("REVIEW_POSITIONING")
        candidates.append(_notification(
            "UNDERVALUATION_OPPORTUNITY_NOTIFICATION",
            "high",
            "Undervaluation opportunity",
            "Reputation and position support higher price than currently achieved; increase or review recommended.",
            "Market signal UNDERPRICED_RELATIVE_TO_POSITION and actions align on capturing more ADR.",
            sources,
            "include_in_report",
        ))

    # 6. VISIBILITY_ISSUE_NOTIFICATION — low visibility + improve visibility action
    if "LOW_VISIBILITY" in alert_types and "IMPROVE_VISIBILITY" in action_types:
        candidates.append(_notification(
            "VISIBILITY_ISSUE_NOTIFICATION",
            "high",
            "Visibility issue requires action",
            "Visibility score is below threshold; improve OTA presence recommended.",
            "LOW_VISIBILITY alert and IMPROVE_VISIBILITY action both point to visibility as a priority.",
            ["LOW_VISIBILITY", "IMPROVE_VISIBILITY"],
            "include_in_report",
        ))
    elif "LOW_VISIBILITY" in alert_types:
        candidates.append(_notification(
            "VISIBILITY_ISSUE_NOTIFICATION",
            "medium",
            "Low visibility detected",
            "Visibility score is below threshold; consider improving OTA presence.",
            "LOW_VISIBILITY alert indicates visibility as a concern.",
            ["LOW_VISIBILITY"],
            "include_in_report",
        ))

    # 7. Price decrease / overpriced risk — if we have PRICE_DECREASE and overpriced signals
    if "PRICE_DECREASE" in action_types and (
        "OVERPRICED_FOR_CURRENT_DEMAND" in signal_types or "PRICE_TOO_HIGH_FOR_DEMAND" in alert_types
    ):
        sources = ["PRICE_DECREASE"]
        if "OVERPRICED_FOR_CURRENT_DEMAND" in signal_types:
            sources.append("OVERPRICED_FOR_CURRENT_DEMAND")
        if "PRICE_TOO_HIGH_FOR_DEMAND" in alert_types:
            sources.append("PRICE_TOO_HIGH_FOR_DEMAND")
        if not any(c.get("type") == "DEMAND_RISK_NOTIFICATION" for c in candidates):
            candidates.append(_notification(
                "DEMAND_RISK_NOTIFICATION",
                "high",
                "Price aligned to demand risk",
                "Pricing may be too high for current demand; decrease or hold recommended.",
                "PRICE_DECREASE action and overpriced signals align on reducing price pressure.",
                sources,
                "include_in_report",
            ))

    # Deduplicate by type: keep highest priority per type
    by_type = {}
    for n in candidates:
        t = n["type"]
        if t not in by_type or PRIORITY_ORDER.get(n["priority"], 0) > PRIORITY_ORDER.get(by_type[t]["priority"], 0):
            by_type[t] = n

    ordered = sorted(
        by_type.values(),
        key=lambda x: -PRIORITY_ORDER.get(x["priority"], 0),
    )
    notification_candidates = ordered
    top_notifications = ordered[:MAX_TOP_NOTIFICATIONS]

    notification_summary = _build_notification_summary(top_notifications)
    notification_priority_counts = _build_priority_counts(top_notifications)

    return {
        "notification_candidates": notification_candidates,
        "top_notifications": top_notifications,
        "notification_summary": notification_summary,
        "notification_priority_counts": notification_priority_counts,
    }


def _build_notification_summary(notifications: list) -> str:
    """Una frase resumen de las notificaciones prioritarias."""
    if not notifications:
        return "No hay notificaciones prioritarias."
    urgent = sum(1 for n in notifications if n.get("priority") == "urgent")
    high = sum(1 for n in notifications if n.get("priority") == "high")
    if urgent:
        return f"{urgent} notificación(es) urgente(s), {high} de prioridad alta. Requieren atención en el informe."
    if high:
        return f"{len(notifications)} notificación(es) prioritarias, {high} de prioridad alta."
    return f"{len(notifications)} notificación(es) para incluir en el informe."


def _build_priority_counts(notifications: list) -> dict:
    """Cuenta por prioridad (urgent, high, medium, low)."""
    counts = {"urgent": 0, "high": 0, "medium": 0, "low": 0}
    for n in notifications:
        p = n.get("priority")
        if p in counts:
            counts[p] += 1
    return counts
