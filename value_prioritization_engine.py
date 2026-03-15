"""
RevMax — Value Prioritization Engine (Fase 12)
==============================================
Calcula value_score, urgency_score, priority_score y priority_rank
para oportunidades y acciones, de modo que RevMax priorice por valor económico
y urgencia sin depender del LLM.
"""

from typing import Optional

# Escalas 0–5 para value y urgency; priority_score = value + urgency (0–10)
VALUE_SCALE = (0.0, 5.0)
URGENCY_SCALE = (0.0, 5.0)


def _get_prioritization_context(briefing: dict) -> dict:
    """Extrae contexto para scoring: alertas, señales, estrategia, estado."""
    alerts = briefing.get("alerts", [])
    alert_types = {a.get("type") for a in alerts if a.get("type")}
    has_critical = any(a.get("severity") == "critical" for a in alerts)
    has_high = any(a.get("severity") == "high" for a in alerts)
    market_signals = briefing.get("market_signals", [])
    signal_types = {s.get("type") for s in market_signals if s.get("type")}
    strategy = (briefing.get("strategy_label") or "BALANCED").upper()
    status = (briefing.get("derived_overall_status") or "stable").lower()
    return {
        "alert_types": alert_types,
        "has_critical_alerts": has_critical,
        "has_high_alerts": has_high,
        "signal_types": signal_types,
        "strategy_label": strategy,
        "derived_overall_status": status,
    }


def _confidence_bonus(conf: str) -> float:
    """Contribución de impact_confidence al value_score (0.3–1.0)."""
    if conf == "high":
        return 1.0
    if conf == "medium":
        return 0.6
    return 0.3


def _opportunity_value_score(opp: dict, ctx: dict) -> float:
    """Value score para una oportunidad (0–5). Basado en tipo, impact_confidence y señales."""
    otype = opp.get("type", "")
    conf = opp.get("impact_confidence", "low")
    base = 1.0
    if otype == "PRICE_CAPTURE_OPPORTUNITY":
        base = 2.5
        if ctx["signal_types"] & {"UNDERPRICED_RELATIVE_TO_POSITION", "DEMAND_SUPPORTS_INCREASE"}:
            base = 3.0
    elif otype == "UNDERVALUATION_OPPORTUNITY":
        base = 2.2
    elif otype == "VISIBILITY_RECOVERY_OPPORTUNITY":
        base = 2.0
    elif otype == "DEMAND_RECOVERY_OPPORTUNITY":
        base = 2.0
    elif otype == "DEFENSIVE_STABILIZATION_OPPORTUNITY":
        base = 2.0
    score = min(VALUE_SCALE[1], base + _confidence_bonus(conf))
    return round(score, 1)


def _opportunity_urgency_score(opp: dict, ctx: dict) -> float:
    """Urgency score para una oportunidad (0–5). Basado en alertas y tipo."""
    otype = opp.get("type", "")
    base = 1.0
    if otype == "DEFENSIVE_STABILIZATION_OPPORTUNITY" and ctx["has_critical_alerts"]:
        base = 3.0
    elif otype == "VISIBILITY_RECOVERY_OPPORTUNITY" and "LOW_VISIBILITY" in ctx["alert_types"]:
        base = 2.5
    elif otype == "DEMAND_RECOVERY_OPPORTUNITY" and ("DEMAND_COLLAPSE" in ctx["alert_types"] or "PRICE_TOO_HIGH_FOR_DEMAND" in ctx["alert_types"]):
        base = 2.5
    elif otype == "PRICE_CAPTURE_OPPORTUNITY" or otype == "UNDERVALUATION_OPPORTUNITY":
        base = 1.5
    if ctx["has_critical_alerts"] and base < 2.0:
        base += 0.5
    return round(min(URGENCY_SCALE[1], base), 1)


def _action_value_score(action: dict, ctx: dict) -> float:
    """Value score para una acción (0–5). Basado en tipo y action_impact_confidence."""
    atype = action.get("type", "")
    conf = action.get("action_impact_confidence", "low")
    base = 1.0
    if atype == "FIX_PARITY":
        base = 2.5
    elif atype == "PRICE_INCREASE":
        base = 2.2
    elif atype == "IMPROVE_VISIBILITY":
        base = 2.0
    elif atype == "PROTECT_RATE":
        base = 2.0
    elif atype == "PRICE_DECREASE":
        base = 1.8
    elif atype == "HOLD_PRICE":
        base = 1.5
    elif atype == "REVIEW_POSITIONING":
        base = 1.5
    elif atype == "MONITOR_DEMAND":
        base = 1.2
    score = min(VALUE_SCALE[1], base + _confidence_bonus(conf))
    return round(score, 1)


def _action_urgency_score(action: dict, ctx: dict) -> float:
    """Urgency score para una acción (0–5). Basado en tipo, alertas y estrategia."""
    atype = action.get("type", "")
    base = 1.0
    if atype == "FIX_PARITY":
        base = 4.0
    elif atype == "IMPROVE_VISIBILITY" and "LOW_VISIBILITY" in ctx["alert_types"]:
        base = 3.0
    elif atype == "PROTECT_RATE" and ctx["has_critical_alerts"]:
        base = 3.0
    elif atype == "PRICE_DECREASE":
        base = 2.0
    elif atype == "PRICE_INCREASE":
        base = 1.5
    elif atype == "HOLD_PRICE":
        base = 1.0
    elif atype == "MONITOR_DEMAND":
        base = 1.5
    elif atype == "REVIEW_POSITIONING":
        base = 1.2
    if ctx["has_critical_alerts"] and atype != "FIX_PARITY":
        base = min(URGENCY_SCALE[1], base + 1.0)
    return round(min(URGENCY_SCALE[1], base), 1)


def _enrich_opportunity(opp: dict, ctx: dict) -> dict:
    """Añade value_score, urgency_score, priority_score; mantiene type, title, impact_estimate, impact_confidence."""
    value_score = _opportunity_value_score(opp, ctx)
    urgency_score = _opportunity_urgency_score(opp, ctx)
    priority_score = round(value_score + urgency_score, 1)
    return {
        "type": opp.get("type", ""),
        "title": opp.get("title", ""),
        "impact_estimate": opp.get("impact_estimate", ""),
        "impact_confidence": opp.get("impact_confidence", "low"),
        "value_score": value_score,
        "urgency_score": urgency_score,
        "priority_score": priority_score,
        "priority_rank": 0,
    }


def _enrich_action(action: dict, ctx: dict) -> dict:
    """Añade value_score, urgency_score, priority_score; mantiene type, title, action_impact_estimate, action_impact_confidence."""
    value_score = _action_value_score(action, ctx)
    urgency_score = _action_urgency_score(action, ctx)
    priority_score = round(value_score + urgency_score, 1)
    return {
        "type": action.get("type", ""),
        "title": action.get("title", ""),
        "action_impact_estimate": action.get("action_impact_estimate", ""),
        "action_impact_confidence": action.get("action_impact_confidence", "low"),
        "value_score": value_score,
        "urgency_score": urgency_score,
        "priority_score": priority_score,
        "priority_rank": 0,
    }


def _assign_ranks(items: list) -> None:
    """Ordena por priority_score DESC y asigna priority_rank 1, 2, 3... in-place."""
    items.sort(key=lambda x: (-x["priority_score"], x.get("title", "")))
    for i, item in enumerate(items, start=1):
        item["priority_rank"] = i


def _pick_top_priority_item(value_opportunities: list, value_actions: list) -> Optional[dict]:
    """Devuelve el elemento (oportunidad o acción) con mayor priority_score; incluye key 'item_type': 'opportunity' | 'action'."""
    candidates = []
    for o in value_opportunities:
        candidates.append({**o, "item_type": "opportunity"})
    for a in value_actions:
        candidates.append({**a, "item_type": "action"})
    if not candidates:
        return None
    return max(candidates, key=lambda x: x["priority_score"])


def _build_value_summary(value_opportunities: list, value_actions: list, top_item: Optional[dict]) -> str:
    """Frase resumen de la priorización."""
    if not value_opportunities and not value_actions:
        return "No items to prioritize."
    parts = []
    if value_opportunities:
        parts.append(f"{len(value_opportunities)} opportunity(ies) ranked by value and urgency.")
    if value_actions:
        parts.append(f"{len(value_actions)} action(s) ranked by value and urgency.")
    if top_item:
        itype = top_item.get("item_type", "item")
        title = top_item.get("title", top_item.get("type", "?"))
        score = top_item.get("priority_score", 0)
        parts.append(f"Top priority ({itype}): {title} (score {score}).")
    return " ".join(parts)


def build_value_prioritization(briefing: dict) -> dict:
    """
    Analiza impact_opportunities, impact_actions, alerts, market_signals, strategy y status.
    Devuelve value_opportunities, value_actions (con value_score, urgency_score, priority_score, priority_rank),
    value_summary y top_priority_item.
    """
    ctx = _get_prioritization_context(briefing)
    impact_opportunities = briefing.get("impact_opportunities", [])
    impact_actions = briefing.get("impact_actions", [])

    value_opportunities = [_enrich_opportunity(o, ctx) for o in impact_opportunities]
    value_actions = [_enrich_action(a, ctx) for a in impact_actions]

    _assign_ranks(value_opportunities)
    _assign_ranks(value_actions)

    top_priority_item = _pick_top_priority_item(value_opportunities, value_actions)
    value_summary = _build_value_summary(value_opportunities, value_actions, top_priority_item)

    return {
        "value_opportunities": value_opportunities,
        "value_actions": value_actions,
        "value_summary": value_summary,
        "top_priority_item": top_priority_item,
    }
