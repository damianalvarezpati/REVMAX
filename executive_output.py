"""
RevMax — Executive Output Layer (Fase 10)
=========================================
Prepara un briefing ejecutivo estructurado para el report agent:
resumen ejecutivo, orden de prioridad, top riesgos/acciones/oportunidades
y decisión sobre incluir memoria. Todo derivado por código.
"""

MAX_TOP_RISKS = 3
MAX_TOP_ACTIONS = 3
MAX_TOP_OPPORTUNITIES = 3

EXECUTIVE_PRIORITY_ORDER = [
    "executive_summary",
    "strategic_posture",
    "critical_risks",
    "recommended_actions",
    "opportunities",
    "market_context",
    "recent_memory",
]


def _build_summary_seed(briefing: dict) -> list[str]:
    """Cuatro puntos cortos: qué pasa, qué necesita atención, oportunidad principal, postura recomendada."""
    strategy = briefing.get("strategy_label", "BALANCED")
    status = briefing.get("derived_overall_status", "stable")
    action = briefing.get("consolidated_price_action", "hold")
    alerts = [a for a in briefing.get("alerts", []) if isinstance(a, dict)]
    opportunities = [o for o in briefing.get("opportunities", []) if isinstance(o, dict)]
    critical_count = briefing.get("alert_critical_count", 0)
    high_count = briefing.get("alert_high_count", 0)

    line1 = f"Postura estratégica: {strategy}. Estado: {status}. Acción consolidada: {action.upper()}."
    if critical_count or high_count:
        top_alert = next((a for a in alerts if a.get("severity") in ("critical", "high")), None)
        line2 = f"Atención: {top_alert.get('type', 'alerta')} — {top_alert.get('message', '')[:80]}." if top_alert else f"Atención: {critical_count} crítica(s), {high_count} alta(s)."
    else:
        line2 = "Nada crítico que requiera atención inmediata."
    high_opps = [o for o in opportunities if o.get("opportunity_level") == "high"]
    if high_opps:
        o = high_opps[0]
        line3 = f"Oportunidad principal: {o.get('title', '')} — {(o.get('summary') or '')[:70]}."
    else:
        line3 = "Oportunidad: mantener postura y estabilidad según señales."
    line4 = f"Postura recomendada: {action.upper()} (consolidación y estrategia alineadas)."
    return [line1, line2, line3, line4]


def _build_section_hints(briefing: dict) -> dict:
    """Una línea por sección para guiar al report agent."""
    return {
        "executive_summary": "Resumen en 4 líneas: qué pasa, qué necesita atención, oportunidad principal, postura recomendada. Usar executive_summary_seed.",
        "strategic_posture": "Estrategia actual (strategy_label) y por qué. Una frase sobre influencia en la decisión.",
        "critical_risks": "Solo los riesgos/alertas en executive_top_risks. Máximo 2-3. Sin repetir lo ya dicho en resumen.",
        "recommended_actions": "Solo las acciones en executive_top_actions. Máximo 3. Qué hacer, por qué, trazable.",
        "opportunities": "Solo las oportunidades en executive_top_opportunities. Máximo 2-3. Diferenciar de riesgos y acciones.",
        "market_context": "Contexto de demanda, señales de mercado y posición. Breve. Sin repetir detalles ya citados.",
        "recent_memory": "Solo si executive_include_memory es True. Cambios vs corrida anterior en una frase. Omitir si no aporta valor.",
    }


def _build_top_risks(briefing: dict) -> list[dict]:
    """Top 2-3 riesgos: critical primero, luego high. Solo type, severity, message corto."""
    alerts = [a for a in briefing.get("alerts", []) if isinstance(a, dict)]
    critical = [a for a in alerts if a.get("severity") == "critical"]
    high = [a for a in alerts if a.get("severity") == "high"]
    ordered = critical + high
    out = []
    for a in ordered[:MAX_TOP_RISKS]:
        out.append({
            "type": a.get("type", "ALERT"),
            "severity": a.get("severity", "high"),
            "message": (a.get("message", "") or "")[:120],
        })
    return out


def _build_top_actions(briefing: dict) -> list[dict]:
    """Top 3 acciones: ya vienen ordenadas por prioridad en recommended_actions."""
    actions = [a for a in briefing.get("recommended_actions", []) if isinstance(a, dict)]
    return [{"type": a.get("type"), "priority": a.get("priority"), "title": a.get("title"), "horizon": a.get("horizon"), "rationale": (a.get("rationale") or "")[:100]} for a in actions[:MAX_TOP_ACTIONS]]


def _build_top_opportunities(briefing: dict) -> list[dict]:
    """Top 2-3 oportunidades: high primero, luego medium."""
    opportunities = [o for o in briefing.get("opportunities", []) if isinstance(o, dict)]
    high_first = sorted(opportunities, key=lambda o: (0 if o.get("opportunity_level") == "high" else 1, 0 if o.get("opportunity_level") == "medium" else 1))
    return [{"type": o.get("type"), "opportunity_level": o.get("opportunity_level"), "title": o.get("title"), "summary": (o.get("summary") or "")[:100], "recommended_posture": o.get("recommended_posture")} for o in high_first[:MAX_TOP_OPPORTUNITIES]]


def _should_include_memory(briefing: dict) -> bool:
    """Incluir memoria solo si hay corrida previa y cambios relevantes."""
    if not briefing.get("previous_snapshot_found"):
        return False
    if briefing.get("repeated_alerts"):
        return True
    if briefing.get("resolved_alerts"):
        return True
    if briefing.get("strategy_changed"):
        return True
    if briefing.get("overall_status_changed"):
        return True
    if briefing.get("attention_trend", "stable") != "stable":
        return True
    return False


def build_executive_briefing(briefing: dict) -> dict:
    """
    A partir del briefing completo, construye el add-on ejecutivo:
    executive_summary_seed, executive_priority_order, executive_section_hints,
    executive_top_risks, executive_top_actions, executive_top_opportunities,
    executive_include_memory.
    """
    return {
        "executive_summary_seed": _build_summary_seed(briefing),
        "executive_priority_order": EXECUTIVE_PRIORITY_ORDER,
        "executive_section_hints": _build_section_hints(briefing),
        "executive_top_risks": _build_top_risks(briefing),
        "executive_top_actions": _build_top_actions(briefing),
        "executive_top_opportunities": _build_top_opportunities(briefing),
        "executive_include_memory": _should_include_memory(briefing),
    }
