"""
RevMax — Opportunity Engine (Fase 9)
====================================
Detecta oportunidades concretas de captura de valor o mejora de posicionamiento.
Generado por código, no por LLM. Diferenciado de alertas y acciones.
"""

from typing import Optional

OPPORTUNITY_LEVELS = ("low", "medium", "high")
MAX_OPPORTUNITIES = 5
LEVEL_ORDER = {"high": 3, "medium": 2, "low": 1}


def _safe_type_string(obj) -> Optional[str]:
    """Extrae un tipo hashable (str) de un item; evita unhashable type: 'dict'."""
    if obj is None:
        return None
    if isinstance(obj, str) and obj.strip():
        return obj.strip()
    if isinstance(obj, (int, float, bool)):
        return str(obj)
    if isinstance(obj, dict):
        return None  # no usar dicts en sets
    return str(obj)[:80] if obj else None


def _opportunity(
    type_: str,
    opportunity_level: str,
    title: str,
    summary: str,
    rationale: str,
    source_items: list,
    potential_value: str,
    recommended_posture: str,
) -> dict:
    return {
        "type": type_,
        "opportunity_level": opportunity_level,
        "title": title,
        "summary": summary,
        "rationale": rationale,
        "source_items": source_items,
        "potential_value": potential_value,
        "recommended_posture": recommended_posture,
    }


def build_opportunities(briefing: dict) -> list[dict]:
    """
    Construye lista de oportunidades coherentes con estrategia, señales, acciones y notificaciones.
    Deduplicado por tipo (mayor level gana). Máximo MAX_OPPORTUNITIES.
    """
    candidates = []
    strategy_label = briefing.get("strategy_label", "BALANCED")
    consolidated_action = briefing.get("consolidated_price_action", "hold")
    alerts = briefing.get("alerts", [])
    market_signals = briefing.get("market_signals", [])
    recommended_actions = briefing.get("recommended_actions", [])
    top_notifications = briefing.get("top_notifications", [])

    alert_types = {_safe_type_string(a.get("type")) for a in alerts if isinstance(a, dict) and _safe_type_string(a.get("type"))}
    signal_types = {_safe_type_string(s.get("type")) for s in market_signals if isinstance(s, dict) and _safe_type_string(s.get("type"))}
    action_types = {_safe_type_string(a.get("type")) for a in recommended_actions if isinstance(a, dict) and _safe_type_string(a.get("type"))}
    has_critical = any(a.get("severity") == "critical" for a in alerts)
    has_high_alert = any(a.get("severity") == "high" for a in alerts)

    # 1. PRICE_CAPTURE_OPPORTUNITY — reputación/posición/demanda permiten capturar más ADR
    if consolidated_action == "raise" and (
        "DEMAND_SUPPORTS_INCREASE" in signal_types or "UNDERPRICED_RELATIVE_TO_POSITION" in signal_types
    ):
        sources = []
        if "DEMAND_SUPPORTS_INCREASE" in signal_types:
            sources.append("DEMAND_SUPPORTS_INCREASE")
        if "UNDERPRICED_RELATIVE_TO_POSITION" in signal_types:
            sources.append("UNDERPRICED_RELATIVE_TO_POSITION")
        if strategy_label == "PREMIUM":
            sources.append("strategy_PREMIUM")
        if strategy_label == "AGGRESSIVE":
            sources.append("strategy_AGGRESSIVE")
        if "COMPETITOR_PRICE_PRESSURE" in signal_types:
            comp_raise = [s for s in market_signals if s.get("type") == "COMPETITOR_PRICE_PRESSURE" and s.get("directional_effect") == "raise"]
            if comp_raise:
                sources.append("COMPETITOR_PRICE_PRESSURE")
        if not sources:
            sources = ["consolidated_raise"]
        level = "high" if len(sources) >= 2 else "medium"
        candidates.append(_opportunity(
            "PRICE_CAPTURE_OPPORTUNITY",
            level,
            "Opportunity to capture additional ADR",
            "Current positioning suggests room to increase price without materially weakening competitiveness.",
            "Demand, reputation and/or current ranking suggest the hotel may be leaving value on the table.",
            sources,
            "adr_capture",
            "raise",
        ))

    # 2. UNDERVALUATION_OPPORTUNITY — hotel infravalorado vs posicionamiento/reputación
    if "UNDERPRICED_RELATIVE_TO_POSITION" in signal_types:
        if not any(c.get("type") == "PRICE_CAPTURE_OPPORTUNITY" for c in candidates):
            sources = ["UNDERPRICED_RELATIVE_TO_POSITION"]
            if "PRICE_INCREASE" in action_types:
                sources.append("PRICE_INCREASE")
            if "REVIEW_POSITIONING" in action_types:
                sources.append("REVIEW_POSITIONING")
            if strategy_label == "PREMIUM":
                sources.append("strategy_PREMIUM")
            level = "high" if "PRICE_INCREASE" in action_types or strategy_label == "PREMIUM" else "medium"
            candidates.append(_opportunity(
                "UNDERVALUATION_OPPORTUNITY",
                level,
                "Undervaluation vs positioning and reputation",
                "Reputation and position support higher price than currently achieved; opportunity to capture more ADR when market allows.",
                "Market signal UNDERPRICED_RELATIVE_TO_POSITION indicates room to improve price positioning.",
                sources,
                "positioning",
                "raise" if consolidated_action == "raise" else "review",
            ))

    # 3. DEFENSIVE_STABILIZATION_OPPORTUNITY — proteger ingresos/posición evitando movimientos arriesgados
    if strategy_label == "DEFENSIVE" and (has_critical or has_high_alert or "PROTECT_RATE" in action_types or "HOLD_PRICE" in action_types):
        sources = ["strategy_DEFENSIVE"]
        if has_critical:
            sources.append("alerts_critical")
        if has_high_alert:
            sources.append("alerts_high")
        if "PROTECT_RATE" in action_types:
            sources.append("PROTECT_RATE")
        if "HOLD_PRICE" in action_types:
            sources.append("HOLD_PRICE")
        level = "high" if has_critical or "PROTECT_RATE" in action_types else "medium"
        candidates.append(_opportunity(
            "DEFENSIVE_STABILIZATION_OPPORTUNITY",
            level,
            "Opportunity to stabilize and protect revenue",
            "Defensive posture and active alerts create an opportunity to protect revenue and position by avoiding risky price moves.",
            "Stabilising now can preserve value until alerts are resolved and signals clarify.",
            sources,
            "revenue_protection",
            "hold",
        ))

    # 4. VISIBILITY_RECOVERY_OPPORTUNITY — mejorar visibilidad para destrabar demanda o pricing power
    if "LOW_VISIBILITY" in alert_types and "IMPROVE_VISIBILITY" in action_types:
        candidates.append(_opportunity(
            "VISIBILITY_RECOVERY_OPPORTUNITY",
            "high",
            "Opportunity to recover visibility and unlock demand",
            "Low visibility is limiting demand capture and pricing power; improving OTA presence can unlock both.",
            "LOW_VISIBILITY alert and IMPROVE_VISIBILITY action align on visibility as a lever for growth.",
            ["LOW_VISIBILITY", "IMPROVE_VISIBILITY"],
            "visibility",
            "improve_visibility",
        ))
    elif "LOW_VISIBILITY" in alert_types:
        candidates.append(_opportunity(
            "VISIBILITY_RECOVERY_OPPORTUNITY",
            "medium",
            "Opportunity to improve visibility",
            "Visibility score is below threshold; improving it could support demand and pricing power.",
            "LOW_VISIBILITY alert indicates visibility as an opportunity area.",
            ["LOW_VISIBILITY"],
            "visibility",
            "improve_visibility",
        ))

    # 5. DEMAND_RECOVERY_OPPORTUNITY — reaccionar mejor a debilidad de demanda con ajuste/protección
    if "WEAK_DEMAND_REQUIRES_CAUTION" in signal_types or "DEMAND_COLLAPSE" in alert_types:
        sources = []
        if "WEAK_DEMAND_REQUIRES_CAUTION" in signal_types:
            sources.append("WEAK_DEMAND_REQUIRES_CAUTION")
        if "DEMAND_COLLAPSE" in alert_types:
            sources.append("DEMAND_COLLAPSE")
        if "MONITOR_DEMAND" in action_types:
            sources.append("MONITOR_DEMAND")
        if "PRICE_DECREASE" in action_types:
            sources.append("PRICE_DECREASE")
        if "HOLD_PRICE" in action_types:
            sources.append("HOLD_PRICE")
        if not sources:
            sources = ["WEAK_DEMAND_REQUIRES_CAUTION"] if "WEAK_DEMAND_REQUIRES_CAUTION" in signal_types else ["DEMAND_COLLAPSE"]
        level = "high" if "DEMAND_COLLAPSE" in alert_types else "medium"
        candidates.append(_opportunity(
            "DEMAND_RECOVERY_OPPORTUNITY",
            level,
            "Opportunity to align with weak demand and protect occupancy",
            "Weak or collapsed demand creates an opportunity to adjust posture (hold or lower) and protect occupancy until demand recovers.",
            "Aligning pricing and actions with demand weakness can limit occupancy loss and position for recovery.",
            sources,
            "demand_alignment",
            "hold" if "HOLD_PRICE" in action_types else ("lower" if "PRICE_DECREASE" in action_types else "monitor"),
        ))

    # 6. Consolidated hold with strong signals => opportunity to preserve value (complement to defensive)
    if consolidated_action == "hold" and strategy_label != "DEFENSIVE" and not any(c.get("type") == "DEFENSIVE_STABILIZATION_OPPORTUNITY" for c in candidates):
        if "MARKET_COMPRESSION" in signal_types or "WEAK_DEMAND_REQUIRES_CAUTION" in signal_types:
            sources = ["consolidated_hold"]
            if "MARKET_COMPRESSION" in signal_types:
                sources.append("MARKET_COMPRESSION")
            if "WEAK_DEMAND_REQUIRES_CAUTION" in signal_types:
                sources.append("WEAK_DEMAND_REQUIRES_CAUTION")
            candidates.append(_opportunity(
                "DEFENSIVE_STABILIZATION_OPPORTUNITY",
                "medium",
                "Opportunity to hold position in uncertain market",
                "Hold posture in a compressed or weak-demand environment preserves optionality and avoids overreaction.",
                "Consolidation and signals support holding; opportunity to capture value by not moving prematurely.",
                sources,
                "revenue_protection",
                "hold",
            ))

    # Deduplicate by type: keep highest opportunity_level per type
    by_type = {}
    for opp in candidates:
        t = opp["type"]
        if t not in by_type or LEVEL_ORDER.get(opp["opportunity_level"], 0) > LEVEL_ORDER.get(by_type[t]["opportunity_level"], 0):
            by_type[t] = opp

    ordered = sorted(
        by_type.values(),
        key=lambda x: -LEVEL_ORDER.get(x["opportunity_level"], 0),
    )
    return ordered[:MAX_OPPORTUNITIES]


def build_opportunity_summary(opportunities: list) -> str:
    """Resumen en una frase de las oportunidades detectadas."""
    if not opportunities:
        return "No se han detectado oportunidades concretas en esta corrida."
    high_count = sum(1 for o in opportunities if o.get("opportunity_level") == "high")
    if high_count:
        return f"{len(opportunities)} oportunidad(es) identificadas, {high_count} de nivel alto. Revisar en el informe."
    return f"{len(opportunities)} oportunidad(es) identificadas."


def count_high_opportunities(opportunities: list) -> int:
    """Cuenta oportunidades de nivel high."""
    return sum(1 for o in opportunities if o.get("opportunity_level") == "high")


def get_opportunity_types(opportunities: list) -> list:
    """Lista de tipos de oportunidades presentes. Solo tipos hashables (str)."""
    seen = set()
    for o in opportunities:
        if not isinstance(o, dict):
            t = _safe_type_string(o) if o is not None else None
        else:
            t = _safe_type_string(o.get("type"))
        if t and t not in seen:
            seen.add(t)
    return sorted(seen)
