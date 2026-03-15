"""
RevMax — Impact Engine (Fase 11)
================================
Añade estimaciones heurísticas de impacto a oportunidades y acciones:
impact_estimate, impact_confidence, impact_reason para oportunidades;
action_impact_estimate, action_impact_confidence para acciones.
No es forecasting ni ML; es una capa heurística de valor para priorizar.
"""

from typing import Optional

IMPACT_CONFIDENCE_LEVELS = ("low", "medium", "high")


def _get_context(briefing: dict) -> dict:
    """Extrae contexto para heurísticas (demanda, GRI, ranking). Usa defaults si no está en briefing."""
    demand = briefing.get("demand_index") or {}
    if isinstance(demand, dict):
        demand_score = demand.get("score", briefing.get("demand_score", 50))
        demand_signal = demand.get("signal", briefing.get("demand_signal", "medium"))
    else:
        demand_score = briefing.get("demand_score", 50)
        demand_signal = briefing.get("demand_signal", "medium")
    gri = briefing.get("gri_value")
    if gri is None and isinstance(briefing.get("reputation"), dict):
        gri = (briefing.get("reputation") or {}).get("gri", {}).get("value") or 0
    if gri is None:
        gri = 0
    your_rank = briefing.get("your_rank")
    total = briefing.get("total_compset", 10) or 10
    rank_ratio = (your_rank / total) if (total and your_rank is not None) else 0.5
    return {
        "demand_score": int(demand_score) if demand_score is not None else 50,
        "demand_signal": demand_signal or "medium",
        "gri_value": int(gri) if gri is not None else 0,
        "your_rank": your_rank,
        "total_compset": total,
        "rank_ratio": rank_ratio,
        "has_critical_alerts": any(a.get("severity") == "critical" for a in briefing.get("alerts", [])),
        "strategy_label": briefing.get("strategy_label", "BALANCED"),
        "signal_types": {s.get("type") for s in briefing.get("market_signals", []) if s.get("type")},
    }


def _estimate_opportunity_impact(opp: dict, ctx: dict) -> dict:
    """Añade impact_estimate, impact_confidence, impact_reason a una oportunidad."""
    out = dict(opp)
    otype = opp.get("type", "")
    if otype == "PRICE_CAPTURE_OPPORTUNITY":
        if ctx["demand_score"] > 65 and "UNDERPRICED_RELATIVE_TO_POSITION" in ctx["signal_types"]:
            out["impact_estimate"] = "ADR capture potential estimated between +5% and +10%"
            out["impact_confidence"] = "medium"
            out["impact_reason"] = "Demand strength and underpricing signals suggest additional ADR capture."
        elif ctx["demand_score"] > 55:
            out["impact_estimate"] = "ADR upside potential: +3% to +7%"
            out["impact_confidence"] = "low"
            out["impact_reason"] = "Moderate demand and positioning support some upside."
        else:
            out["impact_estimate"] = "ADR upside potential limited by demand"
            out["impact_confidence"] = "low"
            out["impact_reason"] = "Demand does not strongly support aggressive capture; upside uncertain."
    elif otype == "UNDERVALUATION_OPPORTUNITY":
        if ctx["gri_value"] >= 78 and ctx["rank_ratio"] >= 0.5:
            out["impact_estimate"] = "Potential ADR capture through positioning improvement"
            out["impact_confidence"] = "medium"
            out["impact_reason"] = "Strong reputation and weak rank suggest room to improve price positioning."
        else:
            out["impact_estimate"] = "Potential ADR capture through positioning improvement"
            out["impact_confidence"] = "low"
            out["impact_reason"] = "Reputation and position indicate some upside; confidence is limited."
    elif otype == "VISIBILITY_RECOVERY_OPPORTUNITY":
        out["impact_estimate"] = "Improved OTA visibility may unlock additional demand"
        out["impact_confidence"] = "medium"
        out["impact_reason"] = "Low visibility currently limits demand capture; improvement can support both occupancy and pricing power."
    elif otype == "DEMAND_RECOVERY_OPPORTUNITY":
        out["impact_estimate"] = "Occupancy protection potential if pricing aligns with demand"
        out["impact_confidence"] = "medium"
        out["impact_reason"] = "Aligning with weak demand helps protect occupancy until demand recovers."
    elif otype == "DEFENSIVE_STABILIZATION_OPPORTUNITY":
        if ctx["has_critical_alerts"]:
            out["impact_estimate"] = "Revenue protection by avoiding aggressive pricing"
            out["impact_confidence"] = "high"
            out["impact_reason"] = "Critical alerts indicate protection is priority over growth."
        else:
            out["impact_estimate"] = "Revenue protection by avoiding aggressive pricing"
            out["impact_confidence"] = "medium"
            out["impact_reason"] = "Defensive posture helps stabilise revenue while signals clarify."
    else:
        out["impact_estimate"] = "Impact uncertain"
        out["impact_confidence"] = "low"
        out["impact_reason"] = "No specific heuristic for this opportunity type."
    return out


def _estimate_action_impact(action: dict, ctx: dict) -> dict:
    """Añade action_impact_estimate, action_impact_confidence a una acción."""
    out = dict(action)
    atype = action.get("type", "")
    if atype == "FIX_PARITY":
        out["action_impact_estimate"] = "Restore channel consistency; avoid contract and commission risk"
        out["action_impact_confidence"] = "high"
    elif atype == "PRICE_INCREASE":
        if ctx["demand_score"] > 65:
            out["action_impact_estimate"] = "ADR upside potential +5% to +9% if demand holds"
            out["action_impact_confidence"] = "medium"
        else:
            out["action_impact_estimate"] = "Moderate ADR upside; monitor occupancy"
            out["action_impact_confidence"] = "low"
    elif atype == "PRICE_DECREASE":
        out["action_impact_estimate"] = "Occupancy support; potential revenue trade-off"
        out["action_impact_confidence"] = "medium"
    elif atype == "HOLD_PRICE":
        out["action_impact_estimate"] = "Preserve current position; avoid unnecessary risk"
        out["action_impact_confidence"] = "medium"
    elif atype == "IMPROVE_VISIBILITY":
        out["action_impact_estimate"] = "Unlock demand and pricing power via better OTA presence"
        out["action_impact_confidence"] = "medium"
    elif atype == "PROTECT_RATE":
        out["action_impact_estimate"] = "Revenue protection in uncertain conditions"
        out["action_impact_confidence"] = "medium"
    elif atype == "MONITOR_DEMAND":
        out["action_impact_estimate"] = "Inform future pricing; limit downside from weak demand"
        out["action_impact_confidence"] = "low"
    elif atype == "REVIEW_POSITIONING":
        out["action_impact_estimate"] = "Potential ADR capture when market allows"
        out["action_impact_confidence"] = "low"
    else:
        out["action_impact_estimate"] = "Impact uncertain"
        out["action_impact_confidence"] = "low"
    return out


def _build_impact_summary(opportunity_impacts: list, action_impacts: list) -> str:
    """Una frase resumen del impacto estimado."""
    if not opportunity_impacts and not action_impacts:
        return "No impact estimates generated for this run."
    parts = []
    high_opps = [o for o in opportunity_impacts if o.get("opportunity_level") == "high"]
    if high_opps:
        parts.append(f"{len(high_opps)} high-value opportunity(ies) with impact estimates.")
    if action_impacts:
        parts.append(f"{len(action_impacts)} action(s) with impact estimates.")
    return " ".join(parts) if parts else "Impact estimates attached to opportunities and actions."


def _pick_top_value_opportunity(opportunity_impacts: list) -> Optional[dict]:
    """Devuelve la oportunidad de mayor valor percibido (high level primero, luego por confidence)."""
    if not opportunity_impacts:
        return None
    conf_order = {"high": 3, "medium": 2, "low": 1}
    level_order = {"high": 3, "medium": 2, "low": 1}
    sorted_opps = sorted(
        opportunity_impacts,
        key=lambda o: (
            -level_order.get(o.get("opportunity_level"), 0),
            -conf_order.get(o.get("impact_confidence"), 0),
        ),
    )
    return sorted_opps[0]


def build_impact_estimates(briefing: dict) -> dict:
    """
    Analiza opportunities, recommended_actions, market_signals, demanda, GRI, ranking y estrategia
    del briefing; devuelve opportunity_impacts (oportunidades con impact_*), action_impacts
    (acciones con action_impact_*), impact_summary y top_value_opportunity.
    """
    ctx = _get_context(briefing)
    opportunities = briefing.get("opportunities", [])
    recommended_actions = briefing.get("recommended_actions", [])

    opportunity_impacts = [_estimate_opportunity_impact(o, ctx) for o in opportunities]
    action_impacts = [_estimate_action_impact(a, ctx) for a in recommended_actions]

    impact_summary = _build_impact_summary(opportunity_impacts, action_impacts)
    top_value_opportunity = _pick_top_value_opportunity(opportunity_impacts)

    return {
        "opportunity_impacts": opportunity_impacts,
        "action_impacts": action_impacts,
        "impact_summary": impact_summary,
        "top_value_opportunity": top_value_opportunity,
    }
