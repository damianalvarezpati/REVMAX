"""
RevMax — Alert Engine (Fase 4)
==============================
Detección estructurada de alertas operativas y estratégicas
a partir de agent_outputs, conflicts y consolidation_result.
Las alertas son generadas por código, no por LLM.
"""

# Severidades: info | warning | high | critical
ALERT_SEVERITIES = ("info", "warning", "high", "critical")

# Umbrales para detección
ALERT_CONFIG = {
    "visibility_low_threshold": 0.5,
    "demand_collapse_score_max": 35,
    "strong_reputation_gri_min": 82,
    "undervalue_rank_ratio_min": 0.5,
}


def detect_alerts(
    agent_outputs: dict,
    conflicts: list,
    consolidation_result: dict,
) -> list[dict]:
    """
    Detecta alertas que un director de hotel debería conocer.
    Devuelve lista de dicts: type, severity, message, source.
    """
    alerts = []
    pricing = agent_outputs.get("pricing", {})
    demand = agent_outputs.get("demand", {})
    reputation = agent_outputs.get("reputation", {})
    distribution = agent_outputs.get("distribution", {})

    p_action = pricing.get("recommendation", {}).get("action", "hold")
    demand_signal = demand.get("demand_index", {}).get("signal", "medium")
    demand_score = demand.get("demand_index", {}).get("score")
    your_rank = pricing.get("market_context", {}).get("your_position_rank")
    total = pricing.get("market_context", {}).get("total_compset", 10) or 10
    visibility = distribution.get("visibility_score", 1.0)
    parity_status = distribution.get("rate_parity", {}).get("status", "ok")
    gri_val = reputation.get("gri", {}).get("value") or 0
    can_premium = reputation.get("gri", {}).get("can_command_premium", False)
    price_perception = (reputation.get("sentiment_analysis") or {}).get("price_perception", "") or ""

    # PARITY_VIOLATION
    if parity_status == "violation":
        alerts.append({
            "type": "PARITY_VIOLATION",
            "severity": "critical",
            "message": "Hotel appears cheaper on OTA than direct channel. Resolve rate parity before any price change.",
            "source": "distribution",
        })

    # LOW_VISIBILITY
    try:
        v = float(visibility) if visibility is not None else 1.0
    except (TypeError, ValueError):
        v = 1.0
    if v < ALERT_CONFIG["visibility_low_threshold"]:
        alerts.append({
            "type": "LOW_VISIBILITY",
            "severity": "warning",
            "message": f"Visibility score ({v:.2f}) is below threshold. Consider improving OTA presence before raising prices.",
            "source": "distribution",
        })

    # DEMAND_COLLAPSE
    try:
        d_score = int(demand_score) if demand_score is not None else 50
    except (TypeError, ValueError):
        d_score = 50
    if d_score <= ALERT_CONFIG["demand_collapse_score_max"]:
        alerts.append({
            "type": "DEMAND_COLLAPSE",
            "severity": "high",
            "message": f"Demand index very low (score {d_score}). Prioritise occupancy; avoid aggressive price increases.",
            "source": "demand",
        })

    # PRICE_TOO_HIGH_FOR_DEMAND
    if p_action == "raise" and demand_signal in ("low", "very_low"):
        alerts.append({
            "type": "PRICE_TOO_HIGH_FOR_DEMAND",
            "severity": "high",
            "message": "Pricing recommends raise but demand is low. Consolidation favours hold; do not raise until demand improves.",
            "source": "pricing",
        })

    # REPUTATION_PRICE_MISMATCH
    if can_premium and isinstance(price_perception, str) and "caro" in price_perception.lower():
        alerts.append({
            "type": "REPUTATION_PRICE_MISMATCH",
            "severity": "warning",
            "message": "Reputation supports premium but guests perceive price as high. Balance ADR and perception.",
            "source": "reputation",
        })

    # STRONG_UNDERVALUE
    try:
        gri = int(gri_val) if gri_val is not None else 0
    except (TypeError, ValueError):
        gri = 0
    rank_ratio = (your_rank / total) if total and your_rank is not None else 0
    if gri >= ALERT_CONFIG["strong_reputation_gri_min"] and rank_ratio >= ALERT_CONFIG["undervalue_rank_ratio_min"]:
        alerts.append({
            "type": "STRONG_UNDERVALUE",
            "severity": "warning",
            "message": f"Strong reputation (GRI {gri}) but weak price position (rank {your_rank}/{total}). Opportunity to capture more ADR.",
            "source": "reputation",
        })

    return alerts


def build_alert_summary(alerts: list) -> str:
    """Resumen en una frase de las alertas detectadas."""
    if not alerts:
        return "No alertas críticas detectadas."
    critical = [a for a in alerts if a.get("severity") == "critical"]
    high = [a for a in alerts if a.get("severity") == "high"]
    if critical:
        return f"{len(critical)} alerta(s) crítica(s), {len(high)} alta(s). Revisar antes de actuar."
    if high:
        return f"{len(high)} alerta(s) de severidad alta. Revisar recomendaciones."
    return f"{len(alerts)} alerta(s) de nivel warning/info."


def count_alert_severity(alerts: list, severity: str) -> int:
    """Cuenta alertas de una severidad dada."""
    return sum(1 for a in alerts if a.get("severity") == severity)
