"""
RevMax — Decision Engine / Action Planner (Fase 6)
==================================================
Genera acciones operativas y estratégicas concretas por código
a partir de consolidación, estrategia, alertas y market signals.
El report agent las redacta y contextualiza; no las inventa.
"""

ACTION_PRIORITIES = ("low", "medium", "high", "urgent")
ACTION_HORIZONS = ("immediate", "this_week", "monitor")
MAX_RECOMMENDED_ACTIONS = 5

PRIORITY_ORDER = {"urgent": 4, "high": 3, "medium": 2, "low": 1}
HORIZON_ORDER = {"immediate": 3, "this_week": 2, "monitor": 1}


def _action(
    type_: str,
    priority: str,
    horizon: str,
    title: str,
    rationale: str,
    source_signals: list,
    expected_effect: str,
) -> dict:
    return {
        "type": type_,
        "priority": priority,
        "horizon": horizon,
        "title": title,
        "rationale": rationale,
        "source_signals": source_signals,
        "expected_effect": expected_effect,
    }


def build_recommended_actions(
    agent_outputs: dict,
    conflicts: list,
    consolidation_result: dict,
) -> list[dict]:
    """
    Construye lista de acciones recomendadas coherentes con consolidación,
    estrategia, alertas y market signals. Deduplicado por tipo (mayor prioridad gana).
    Máximo MAX_RECOMMENDED_ACTIONS acciones.
    """
    candidates = []
    briefing = consolidation_result
    consolidated_action = briefing.get("consolidated_price_action", "hold")
    strategy_label = briefing.get("strategy_label", "BALANCED")
    derived_status = briefing.get("derived_overall_status", "stable")
    alerts = briefing.get("alerts", [])
    market_signals = briefing.get("market_signals", [])

    alert_types = {a.get("type") for a in alerts}
    signal_types = {s.get("type") for s in market_signals}
    has_critical = any(a.get("severity") == "critical" for a in alerts)
    has_high_alert = any(a.get("severity") == "high" for a in alerts)

    # 1. FIX_PARITY — parity violation => urgent, immediate
    if "PARITY_VIOLATION" in alert_types:
        candidates.append(_action(
            "FIX_PARITY",
            "urgent",
            "immediate",
            "Resolve rate parity across channels",
            "Rate parity violation detected; hotel appears cheaper on OTA than direct. Must be fixed before any price change.",
            ["PARITY_VIOLATION"],
            "Restore channel consistency and avoid contract/commission issues.",
        ))

    # 2. IMPROVE_VISIBILITY — low visibility alert
    if "LOW_VISIBILITY" in alert_types:
        candidates.append(_action(
            "IMPROVE_VISIBILITY",
            "high",
            "this_week",
            "Improve OTA visibility and presence",
            "Visibility score is below threshold; limits ability to capture demand.",
            ["LOW_VISIBILITY"],
            "Better visibility supports both occupancy and pricing power.",
        ))

    # 3. DEFENSIVE + critical/alert => PROTECT_RATE or HOLD
    if strategy_label == "DEFENSIVE" and (has_critical or derived_status == "alert"):
        candidates.append(_action(
            "PROTECT_RATE",
            "urgent" if has_critical else "high",
            "immediate" if has_critical else "this_week",
            "Protect current rate position",
            "Strategy is DEFENSIVE and there are critical or high-severity alerts; avoid risky moves.",
            ["strategy_DEFENSIVE", "alerts_critical_or_high"],
            "Stabilise position until alerts are resolved.",
        ))

    # 4. DEMAND_COLLAPSE / weak demand => MONITOR_DEMAND + HOLD
    if "DEMAND_COLLAPSE" in alert_types or "WEAK_DEMAND_REQUIRES_CAUTION" in signal_types:
        if not any(c.get("type") == "MONITOR_DEMAND" for c in candidates):
            candidates.append(_action(
                "MONITOR_DEMAND",
                "high" if "DEMAND_COLLAPSE" in alert_types else "medium",
                "this_week",
                "Monitor demand and avoid aggressive pricing",
                "Demand is weak or collapsed; do not raise prices until demand improves.",
                list(signal_types & {"WEAK_DEMAND_REQUIRES_CAUTION"}) or (["DEMAND_COLLAPSE"] if "DEMAND_COLLAPSE" in alert_types else []),
                "Avoid further occupancy loss; revisit when demand recovers.",
            ))

    # 5. OVERPRICED / PRICE_TOO_HIGH => PRICE_DECREASE or HOLD
    if "OVERPRICED_FOR_CURRENT_DEMAND" in signal_types or "PRICE_TOO_HIGH_FOR_DEMAND" in alert_types:
        candidates.append(_action(
            "PRICE_DECREASE",
            "high",
            "this_week",
            "Reduce price to align with current demand",
            "Pricing or signals indicate posture may be too high for current demand; consolidation favours hold or lower.",
            list(signal_types & {"OVERPRICED_FOR_CURRENT_DEMAND"}) or (["PRICE_TOO_HIGH_FOR_DEMAND"] if "PRICE_TOO_HIGH_FOR_DEMAND" in alert_types else []),
            "Improve occupancy and alignment with market.",
        ))

    # 6. Consolidated raise + supporting signals => PRICE_INCREASE
    if consolidated_action == "raise":
        sources = []
        if "DEMAND_SUPPORTS_INCREASE" in signal_types:
            sources.append("DEMAND_SUPPORTS_INCREASE")
        if "UNDERPRICED_RELATIVE_TO_POSITION" in signal_types:
            sources.append("UNDERPRICED_RELATIVE_TO_POSITION")
        comp_raise = [s for s in market_signals if s.get("type") == "COMPETITOR_PRICE_PRESSURE" and s.get("directional_effect") == "raise"]
        if comp_raise:
            sources.append("COMPETITOR_PRICE_PRESSURE")
        if not sources:
            sources.append("consolidated_raise")
        candidates.append(_action(
            "PRICE_INCREASE",
            "high" if sources else "medium",
            "this_week",
            "Increase price positioning",
            "Consolidation recommends raise; demand and/or reputation support capturing more ADR.",
            sources,
            "Improve ADR capture without weakening competitive position.",
        ))

    # 7. Consolidated lower => PRICE_DECREASE (if not already added)
    if consolidated_action == "lower" and not any(c.get("type") == "PRICE_DECREASE" for c in candidates):
        candidates.append(_action(
            "PRICE_DECREASE",
            "high",
            "this_week",
            "Reduce price as recommended",
            "Consolidation recommends lower; align with demand and competition.",
            ["consolidated_lower"],
            "Stimulate demand and improve occupancy.",
        ))

    # 8. Consolidated hold + caution => HOLD_PRICE
    if consolidated_action == "hold":
        sources = ["consolidated_hold"]
        if "WEAK_DEMAND_REQUIRES_CAUTION" in signal_types:
            sources.append("WEAK_DEMAND_REQUIRES_CAUTION")
        if "MARKET_COMPRESSION" in signal_types:
            sources.append("MARKET_COMPRESSION")
        if strategy_label == "DEFENSIVE":
            sources.append("strategy_DEFENSIVE")
        candidates.append(_action(
            "HOLD_PRICE",
            "high" if has_critical or has_high_alert else "medium",
            "this_week",
            "Hold current price",
            "Consolidation recommends hold; signals support maintaining current posture.",
            sources,
            "Preserve position until signals clarify.",
        ))

    # 9. COMPETITOR_PRICE_PRESSURE / UNDERPRICED without raise => REVIEW_POSITIONING
    if "UNDERPRICED_RELATIVE_TO_POSITION" in signal_types and consolidated_action != "raise":
        if not any(c.get("type") == "PRICE_INCREASE" for c in candidates):
            candidates.append(_action(
                "REVIEW_POSITIONING",
                "medium",
                "this_week",
                "Review price positioning vs reputation",
                "Reputation supports premium but current price does not reflect it; consider gradual increase when demand allows.",
                ["UNDERPRICED_RELATIVE_TO_POSITION"],
                "Capture more ADR when market supports it.",
            ))

    # Deduplicate by type: keep highest priority per type
    by_type = {}
    for act in candidates:
        t = act["type"]
        if t not in by_type or PRIORITY_ORDER.get(act["priority"], 0) > PRIORITY_ORDER.get(by_type[t]["priority"], 0):
            by_type[t] = act

    # Sort: priority desc, then horizon desc (immediate first)
    ordered = sorted(
        by_type.values(),
        key=lambda a: (-PRIORITY_ORDER.get(a["priority"], 0), -HORIZON_ORDER.get(a["horizon"], 0)),
    )
    return ordered[:MAX_RECOMMENDED_ACTIONS]


def build_recommended_action_summary(actions: list) -> str:
    """Resumen en una frase de las acciones recomendadas."""
    if not actions:
        return "No hay acciones recomendadas por el planificador."
    urgent = sum(1 for a in actions if a.get("priority") == "urgent")
    high = sum(1 for a in actions if a.get("priority") == "high")
    if urgent:
        return f"{urgent} acción(es) urgente(s), {high} de prioridad alta. Revisar en orden."
    if high:
        return f"{len(actions)} acción(es) recomendadas, {high} de prioridad alta."
    return f"{len(actions)} acción(es) recomendadas."


def count_actions_by_priority(actions: list, priority: str) -> int:
    """Cuenta acciones con la prioridad dada."""
    return sum(1 for a in actions if a.get("priority") == priority)
