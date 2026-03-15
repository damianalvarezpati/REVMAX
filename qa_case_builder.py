"""
RevMax — QA Case Builder
========================
Construye casos de validación humana a partir del briefing.
Cada caso es legible, estructurado y preparado para revisión humana.
No modifica consolidate ni ningún engine; solo lee el briefing.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


def _slug(s: str) -> str:
    """Nombre seguro para archivos."""
    if not s:
        return "unknown"
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in (s or "").strip())[:64]


def _observed_facts(briefing: dict) -> dict:
    """
    Hechos observables realmente presentes en el briefing.
    Incluye demand, parity (inferido de alertas si aplica), visibilidad si existe,
    pricing position, GRI, alertas, market signals, compset sold out / pick-up si existen.
    """
    alerts = briefing.get("alerts") or []
    market_signals = briefing.get("market_signals") or []
    demand_score = briefing.get("demand_score")
    demand_signal = (briefing.get("demand_signal") or "medium").lower()
    your_rank = briefing.get("your_rank")
    total_compset = briefing.get("total_compset")
    gri_value = briefing.get("gri_value")

    parity_status = "ok"
    for a in alerts:
        t = (a.get("type") or "").upper()
        if "PARITY" in t or t == "RATE_PARITY_VIOLATION":
            parity_status = "violation"
            break

    visibility = briefing.get("visibility_score")
    if visibility is None and "distribution" in briefing:
        visibility = (briefing.get("distribution") or {}).get("visibility_score")

    alert_types = [a.get("type") for a in alerts if a.get("type")]
    signal_types = [s.get("type") for s in market_signals if s.get("type")]

    facts = {
        "demand_score": demand_score,
        "demand_signal": demand_signal,
        "parity_status": parity_status,
        "visibility": visibility if visibility is not None else "N/A",
        "pricing_position_rank": your_rank,
        "pricing_total_compset": total_compset,
        "reputation_gri": gri_value,
        "alerts_detected": [{"type": a.get("type"), "severity": a.get("severity"), "message": (a.get("message") or "")[:200]} for a in alerts[:15]],
        "alert_types": alert_types,
        "market_signals": [{"type": s.get("type"), "effect": s.get("effect"), "summary": (s.get("summary") or "")[:150]} for s in market_signals[:10]],
        "market_signal_types": signal_types,
    }

    compset_sold_out = None
    pickup_signal = None
    compression_signal = None
    for a in alerts:
        t = (a.get("type") or "").upper()
        if "SOLD_OUT" in t or t == "COMPETITOR_SOLD_OUT":
            compset_sold_out = a.get("message") or True
        if "PICKUP" in t or "PICK_UP" in t:
            pickup_signal = a.get("message") or True
    for s in market_signals:
        t = (s.get("type") or "").upper()
        if "COMPRESSION" in t:
            compression_signal = s.get("summary") or True
    if compset_sold_out is not None:
        facts["compset_sold_out_signal"] = compset_sold_out
    if pickup_signal is not None:
        facts["pickup_signal"] = pickup_signal
    if compression_signal is not None:
        facts["compression_signal"] = compression_signal

    return facts


def _interpreted_signals(briefing: dict) -> dict:
    """Resumen de qué interpreta RevMax: strategy_label, derived_overall_status, consolidated_price_action, recommended_scenario, top_priority_item."""
    strategy_label = briefing.get("strategy_label") or "BALANCED"
    derived_overall_status = briefing.get("derived_overall_status") or "stable"
    consolidated_price_action = (briefing.get("consolidated_price_action") or "hold").lower()
    recommended_scenario = briefing.get("recommended_scenario") or consolidated_price_action

    top_priority_item = briefing.get("top_priority_item")
    top_priority_text = None
    if top_priority_item:
        itype = top_priority_item.get("item_type", "item")
        title = top_priority_item.get("title") or top_priority_item.get("type") or "?"
        score = top_priority_item.get("priority_score")
        top_priority_text = f"{itype}: {title} (score {score})" if score is not None else f"{itype}: {title}"

    return {
        "strategy_label": strategy_label,
        "derived_overall_status": derived_overall_status,
        "consolidated_price_action": consolidated_price_action,
        "recommended_scenario": recommended_scenario,
        "top_priority_item": top_priority_text,
        "strategy_rationale": briefing.get("strategy_rationale"),
        "strategy_confidence": briefing.get("strategy_confidence"),
        "strategy_influence_on_decision": briefing.get("strategy_influence_on_decision"),
    }


def _system_verdict(briefing: dict) -> dict:
    """overall_position, recommended_posture, priority_level."""
    status = briefing.get("derived_overall_status") or "stable"
    action = (briefing.get("consolidated_price_action") or "hold").lower()
    priority_level = "high" if briefing.get("alert_critical_count") or briefing.get("urgent_action_count") else ("medium" if briefing.get("alert_high_count") or briefing.get("high_priority_action_count") else "normal")
    return {
        "overall_position": status,
        "recommended_posture": action,
        "priority_level": priority_level,
    }


def _why_this_conclusion(briefing: dict) -> dict:
    """Drivers principales, riesgos principales, trade-offs, por qué el escenario recomendado es defendible."""
    drivers = briefing.get("decision_drivers") or []
    penalties = briefing.get("decision_penalties") or []
    scenario_summary = briefing.get("scenario_summary")
    scenario_risks = briefing.get("scenario_risks") or []
    scenario_tradeoffs = briefing.get("scenario_tradeoffs") or []
    consolidation_rationale = briefing.get("consolidation_rationale")

    return {
        "main_drivers": drivers if isinstance(drivers, list) else [drivers],
        "main_risks": penalties if isinstance(penalties, list) else [penalties],
        "scenario_risks": scenario_risks,
        "trade_offs": scenario_tradeoffs,
        "why_recommended_scenario_defendable": scenario_summary or consolidation_rationale or "Derived from support/risk scores and consolidation logic.",
    }


def build_validation_case_from_briefing(
    briefing: dict,
    hotel_name: str,
    scenario_name: Optional[str] = None,
) -> dict:
    """
    Construye un caso de validación legible y estructurado a partir del briefing.
    No modifica el briefing. Funciona con briefing incompleto (keys opcionales).
    """
    if not briefing:
        briefing = {}

    test_id = str(uuid.uuid4())[:8]
    timestamp = datetime.utcnow().isoformat() + "Z"
    scenario_name = scenario_name or (briefing.get("recommended_scenario") or "unknown")

    observed_facts = _observed_facts(briefing)
    interpreted_signals = _interpreted_signals(briefing)
    system_verdict = _system_verdict(briefing)
    why_this_conclusion = _why_this_conclusion(briefing)

    executive_risks = briefing.get("executive_top_risks") or []
    executive_actions = briefing.get("executive_top_actions") or []
    executive_opportunities = briefing.get("executive_top_opportunities") or []

    recommended_actions = []
    for a in (briefing.get("recommended_priority_actions_seed") or executive_actions or [])[:5]:
        if isinstance(a, dict):
            recommended_actions.append({
                "urgency": a.get("urgency"),
                "reason_source": a.get("reason_source"),
                "action_hint": a.get("action_hint") or a.get("title") or a.get("rationale"),
            })
        else:
            recommended_actions.append({"action_hint": str(a)})

    top_risks = []
    for r in executive_risks[:5]:
        if isinstance(r, dict):
            top_risks.append({"type": r.get("type"), "severity": r.get("severity"), "message": (r.get("message") or "")[:200]})
        else:
            top_risks.append({"message": str(r)})
    if not top_risks and briefing.get("alerts"):
        for a in (briefing.get("alerts") or [])[:3]:
            if a.get("severity") in ("critical", "high"):
                top_risks.append({"type": a.get("type"), "severity": a.get("severity"), "message": (a.get("message") or "")[:200]})

    top_opportunities = []
    for o in executive_opportunities[:5]:
        if isinstance(o, dict):
            top_opportunities.append({"type": o.get("type"), "title": o.get("title"), "summary": (o.get("summary") or "")[:150]})
        else:
            top_opportunities.append({"summary": str(o)})
    if not top_opportunities and briefing.get("opportunities"):
        for o in (briefing.get("opportunities") or [])[:3]:
            if isinstance(o, dict):
                top_opportunities.append({"type": o.get("type"), "title": o.get("title"), "summary": (o.get("summary") or "")[:150]})

    return {
        "test_id": test_id,
        "timestamp": timestamp,
        "hotel_name": hotel_name,
        "scenario_name": scenario_name,
        "observed_facts": observed_facts,
        "interpreted_signals": interpreted_signals,
        "system_verdict": system_verdict,
        "recommended_actions": recommended_actions,
        "recommended_scenario": briefing.get("recommended_scenario") or briefing.get("consolidated_price_action") or "hold",
        "top_risks": top_risks,
        "top_opportunities": top_opportunities,
        "why_this_conclusion": why_this_conclusion,
        "human_score": None,
        "human_feedback": None,
        "human_verdict": None,
        "adjustment_decision": None,
    }
