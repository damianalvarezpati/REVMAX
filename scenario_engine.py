"""
RevMax — Scenario / Recommendation Engine (Fase 13)
==================================================
Compara escenarios de postura (raise, hold, lower) con heurísticas explícitas:
support_score, risk_score, net_score, verdict y razón por escenario.
No reemplaza consolidate(); lo complementa con comparación explícita.
"""

SCENARIOS = ("raise", "hold", "lower")
VERDICT_STRONG = "strong"
VERDICT_MEDIUM = "medium"
VERDICT_WEAK = "weak"
SCORE_CAP = 5.0


def _get_scenario_context(briefing: dict) -> dict:
    """Extrae contexto para evaluar escenarios."""
    alerts = briefing.get("alerts", [])
    alert_types = {a.get("type") for a in alerts if a.get("type")}
    has_critical = any(a.get("severity") == "critical" for a in alerts)
    has_high = any(a.get("severity") == "high" for a in alerts)
    market_signals = briefing.get("market_signals", [])
    signal_types = {s.get("type") for s in market_signals if s.get("type")}
    demand = briefing.get("demand_index") or {}
    if isinstance(demand, dict):
        demand_score = demand.get("score", briefing.get("demand_score", 50))
        demand_signal = (demand.get("signal") or briefing.get("demand_signal", "medium")).lower()
    else:
        demand_score = briefing.get("demand_score", 50)
        demand_signal = (briefing.get("demand_signal") or "medium").lower()
    demand_score = int(demand_score) if demand_score is not None else 50
    strategy = (briefing.get("strategy_label") or "BALANCED").upper()
    consolidated = (briefing.get("consolidated_price_action") or "hold").lower()
    action_types = {a.get("type") for a in briefing.get("recommended_actions", []) if a.get("type")}
    return {
        "alert_types": alert_types,
        "has_critical_alerts": has_critical,
        "has_high_alerts": has_high,
        "signal_types": signal_types,
        "demand_score": demand_score,
        "demand_signal": demand_signal,
        "strategy_label": strategy,
        "consolidated_price_action": consolidated,
        "action_types": action_types,
    }


def _score_raise(ctx: dict) -> tuple:
    """support_score, risk_score para escenario raise."""
    support = 0.0
    risk = 0.0
    # Support: demand strong, underpriced, premium strategy
    if ctx["demand_signal"] == "high" or ctx["demand_score"] > 65:
        support += 1.5
    if "UNDERPRICED_RELATIVE_TO_POSITION" in ctx["signal_types"]:
        support += 1.2
    if "DEMAND_SUPPORTS_INCREASE" in ctx["signal_types"]:
        support += 1.0
    if ctx["strategy_label"] == "PREMIUM":
        support += 0.8
    if "PRICE_INCREASE" in ctx["action_types"]:
        support += 0.5
    # Risk: parity violation, weak demand, defensive, overpriced
    if "PARITY_VIOLATION" in ctx["alert_types"] or ctx["has_critical_alerts"]:
        risk += 2.0
    if ctx["demand_signal"] == "low" or ctx["demand_score"] < 45:
        risk += 1.5
    if ctx["strategy_label"] == "DEFENSIVE":
        risk += 1.2
    if "OVERPRICED_FOR_CURRENT_DEMAND" in ctx["signal_types"] or "PRICE_TOO_HIGH_FOR_DEMAND" in ctx["alert_types"]:
        risk += 1.5
    if "LOW_VISIBILITY" in ctx["alert_types"]:
        risk += 0.5
    support = min(SCORE_CAP, round(support, 1))
    risk = min(SCORE_CAP, round(risk, 1))
    return support, risk


def _score_hold(ctx: dict) -> tuple:
    """support_score, risk_score para escenario hold."""
    support = 0.0
    risk = 0.0
    # Support: defensive, parity (hold until fixed), weak demand, market compression
    if ctx["strategy_label"] == "DEFENSIVE":
        support += 1.5
    if "PARITY_VIOLATION" in ctx["alert_types"]:
        support += 1.2
    if ctx["demand_signal"] == "low" or ctx["demand_score"] < 50:
        support += 0.8
    if "MARKET_COMPRESSION" in ctx["signal_types"]:
        support += 0.8
    if "HOLD_PRICE" in ctx["action_types"] or ctx["consolidated_price_action"] == "hold":
        support += 0.5
    if ctx["has_critical_alerts"]:
        support += 1.0
    # Risk: opportunity cost when demand strong and underpriced
    if (ctx["demand_signal"] == "high" or ctx["demand_score"] > 65) and "UNDERPRICED_RELATIVE_TO_POSITION" in ctx["signal_types"]:
        risk += 1.0
    support = min(SCORE_CAP, round(support, 1))
    risk = min(SCORE_CAP, round(risk, 1))
    return support, risk


def _score_lower(ctx: dict) -> tuple:
    """support_score, risk_score para escenario lower."""
    support = 0.0
    risk = 0.0
    # Support: overpriced, weak demand, demand collapse
    if "OVERPRICED_FOR_CURRENT_DEMAND" in ctx["signal_types"] or "PRICE_TOO_HIGH_FOR_DEMAND" in ctx["alert_types"]:
        support += 1.8
    if ctx["demand_signal"] == "low" or ctx["demand_score"] < 45:
        support += 1.2
    if "DEMAND_COLLAPSE" in ctx["alert_types"]:
        support += 1.2
    if "PRICE_DECREASE" in ctx["action_types"]:
        support += 0.5
    # Risk: strong demand, premium strategy
    if ctx["demand_signal"] == "high" or ctx["demand_score"] > 65:
        risk += 1.8
    if ctx["strategy_label"] == "PREMIUM":
        risk += 1.0
    if "UNDERPRICED_RELATIVE_TO_POSITION" in ctx["signal_types"]:
        risk += 1.0
    support = min(SCORE_CAP, round(support, 1))
    risk = min(SCORE_CAP, round(risk, 1))
    return support, risk


def _verdict_from_net(net_score: float) -> str:
    if net_score >= 2.0:
        return VERDICT_STRONG
    if net_score >= 0.0:
        return VERDICT_MEDIUM
    return VERDICT_WEAK


def _reason_raise(support: float, risk: float, ctx: dict) -> str:
    parts = []
    if risk >= 2.0 and "PARITY_VIOLATION" in ctx["alert_types"]:
        parts.append("Raise is constrained by active parity risk.")
    if ctx["demand_signal"] == "low" and risk > 0:
        parts.append("Weak demand does not support raising price.")
    if ctx["strategy_label"] == "DEFENSIVE" and risk > 0:
        parts.append("Defensive posture penalises raise.")
    if support >= 2.0 and "UNDERPRICED_RELATIVE_TO_POSITION" in ctx["signal_types"]:
        parts.append("Underpriced signal and demand support raise.")
    if not parts:
        parts.append("Raise has mixed support and risk from current signals.")
    return " ".join(parts)


def _reason_hold(support: float, risk: float, ctx: dict) -> str:
    parts = []
    if "PARITY_VIOLATION" in ctx["alert_types"] or ctx["has_critical_alerts"]:
        parts.append("Hold aligns with resolving critical issues first.")
    if ctx["strategy_label"] == "DEFENSIVE":
        parts.append("Hold aligns with defensive posture and current alert profile.")
    if ctx["demand_signal"] == "low":
        parts.append("Hold is consistent with weak demand.")
    if not parts:
        parts.append("Hold balances support and risk given current signals.")
    return " ".join(parts)


def _reason_lower(support: float, risk: float, ctx: dict) -> str:
    parts = []
    if "OVERPRICED_FOR_CURRENT_DEMAND" in ctx["signal_types"] or "PRICE_TOO_HIGH_FOR_DEMAND" in ctx["alert_types"]:
        parts.append("Lower is supported by overpricing signals.")
    if ctx["demand_signal"] == "low":
        parts.append("Weak demand supports lowering to protect occupancy.")
    if risk > 1.5:
        parts.append("Lower carries revenue risk if demand is strong.")
    if not parts:
        parts.append("Lower has mixed support and risk from current signals.")
    return " ".join(parts)


def _build_assessment(ctx: dict) -> list:
    """Lista de dicts con scenario, support_score, risk_score, net_score, verdict, reason."""
    scorers = {
        "raise": (_score_raise, _reason_raise),
        "hold": (_score_hold, _reason_hold),
        "lower": (_score_lower, _reason_lower),
    }
    out = []
    for scenario in SCENARIOS:
        score_fn, reason_fn = scorers[scenario]
        support, risk = score_fn(ctx)
        net = round(support - risk, 1)
        verdict = _verdict_from_net(net)
        reason = reason_fn(support, risk, ctx)
        out.append({
            "scenario": scenario,
            "support_score": support,
            "risk_score": risk,
            "net_score": net,
            "verdict": verdict,
            "reason": reason,
        })
    return out


def _recommended_scenario(assessment: list) -> str:
    """Escenario con mayor net_score; empate: preferir hold sobre raise sobre lower."""
    best = max(assessment, key=lambda x: (x["net_score"], {"hold": 2, "raise": 1, "lower": 0}.get(x["scenario"], 0)))
    return best["scenario"]


def _build_scenario_summary(recommended: str, assessment: list, ctx: dict) -> str:
    """Una frase que explica por qué el escenario recomendado es el más defendible."""
    rec = next(a for a in assessment if a["scenario"] == recommended)
    if recommended == "hold":
        if ctx["has_critical_alerts"] or "PARITY_VIOLATION" in ctx["alert_types"]:
            return "Hold appears the most defendable scenario because critical issues (e.g. parity) should be resolved before any price change."
        if ctx["strategy_label"] == "DEFENSIVE":
            return "Hold appears the most defendable scenario because the defensive posture and current alert profile favour stability."
        if ctx["demand_signal"] == "low":
            return "Hold appears the most defendable scenario because demand is weak and signals do not strongly support raise or lower."
    if recommended == "raise":
        return "Raise appears the most defendable scenario because demand and positioning signals support additional ADR capture."
    if recommended == "lower":
        return "Lower appears the most defendable scenario because overpricing or weak demand signals favour protecting occupancy."
    return f"{recommended.capitalize()} appears the most defendable scenario given current support and risk scores."


def _build_scenario_risks(assessment: list) -> list:
    """Lista de riesgos destacados por escenario."""
    risks = []
    for a in assessment:
        if a["risk_score"] >= 2.0:
            risks.append(f"{a['scenario'].upper()}: high risk ({a['risk_score']}) — {a['reason']}")
        elif a["risk_score"] >= 1.0:
            risks.append(f"{a['scenario'].upper()}: moderate risk ({a['risk_score']})")
    return risks if risks else ["No scenario has elevated risk in current context."]


def _build_scenario_tradeoffs(assessment: list) -> list:
    """Lista de tradeoffs entre escenarios."""
    tradeoffs = []
    strong = [a for a in assessment if a["verdict"] == VERDICT_STRONG]
    weak = [a for a in assessment if a["verdict"] == VERDICT_WEAK]
    if strong and weak:
        tradeoffs.append(f"Choosing {strong[0]['scenario']} over {weak[0]['scenario']} trades off {weak[0]['reason']} for higher net support.")
    if len(assessment) >= 2:
        by_net = sorted(assessment, key=lambda x: -x["net_score"])
        if by_net[0]["net_score"] - by_net[1]["net_score"] < 1.0:
            tradeoffs.append(f"Close call between {by_net[0]['scenario']} and {by_net[1]['scenario']}; recommended scenario has slight edge.")
    return tradeoffs if tradeoffs else ["Scenarios are evaluated with explicit support and risk; recommended scenario has the best net score."]


def build_scenario_assessment(briefing: dict) -> dict:
    """
    Evalúa escenarios raise, hold, lower con support_score, risk_score, net_score, verdict y reason.
    Usa consolidated_price_action, strategy_label, alerts, market_signals, demand, recommended_actions.
    Devuelve scenario_assessment, scenario_summary, recommended_scenario, scenario_risks, scenario_tradeoffs.
    """
    ctx = _get_scenario_context(briefing)
    assessment = _build_assessment(ctx)
    recommended = _recommended_scenario(assessment)
    scenario_summary = _build_scenario_summary(recommended, assessment, ctx)
    scenario_risks = _build_scenario_risks(assessment)
    scenario_tradeoffs = _build_scenario_tradeoffs(assessment)
    return {
        "scenario_assessment": assessment,
        "scenario_summary": scenario_summary,
        "recommended_scenario": recommended,
        "scenario_risks": scenario_risks,
        "scenario_tradeoffs": scenario_tradeoffs,
    }
