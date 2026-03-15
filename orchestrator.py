"""
RevMax — Orquestador Principal v2
====================================
Pipeline completo con los 7 agentes reales.
Agentes 3–6 corren en paralelo con asyncio.gather().
Consolidación: pesos centralizados en CONSOLIDATION_WEIGHTS; lógica en helpers.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Callable, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.agent_01_discovery import run_discovery_agent
from agents.agent_02_compset import run_compset_agent
from agents.agent_03_pricing import run_pricing_agent
from agents.agent_04_demand import run_demand_agent
from agents.agent_05_reputation import run_reputation_agent
from agents.agent_06_distribution import run_distribution_agent
from agents.agent_07_report import run_report_agent
from strategy_engine import (
    derive_strategy,
    apply_strategy_modulation,
    build_strategy_influence_on_decision,
)
from alerts_engine import detect_alerts, build_alert_summary, count_alert_severity
from market_signals import (
    detect_market_signals,
    build_market_signal_summary,
    count_market_signals_by_effect,
)
from action_planner import (
    build_recommended_actions,
    build_recommended_action_summary,
    count_actions_by_priority,
)


# ─────────────────────────────────────────────────────────────────────────────
# Pesos y factores de consolidación. Centralizados para mantenimiento.
# Modificar aquí para ajustar sensibilidad sin tocar la lógica.
# ─────────────────────────────────────────────────────────────────────────────
CONSOLIDATION_WEIGHTS = {
    "reputation_premium_raise_factor": 0.4,
    "reputation_overprice_lower_factor": 0.3,
    "parity_hold_boost": 0.8,
    "parity_raise_lower_multiplier": 0.3,
    "visibility_low_raise_multiplier": 0.6,
    "visibility_low_hold_boost": 0.2,
    "high_conflict_raise_multiplier": 0.5,
    "high_conflict_hold_boost": 0.4,
    "gri_min_for_premium": 78,
    "opportunity_max_count": 5,
    "opportunity_normalize_len": 80,
}


def detect_conflicts(agent_outputs: dict) -> list[dict]:
    conflicts = []
    pricing = agent_outputs.get("pricing", {})
    demand = agent_outputs.get("demand", {})
    reputation = agent_outputs.get("reputation", {})
    distribution = agent_outputs.get("distribution", {})

    price_action = pricing.get("recommendation", {}).get("action", "hold")
    demand_signal = demand.get("demand_index", {}).get("signal", "medium")
    rep_gri = reputation.get("gri", {}).get("value", 0) or 0
    rep_can_premium = reputation.get("gri", {}).get("can_command_premium", False)
    your_rank = pricing.get("market_context", {}).get("your_position_rank", 5)
    total = pricing.get("market_context", {}).get("total_compset", 10) or 10
    visibility = distribution.get("visibility_score", 1.0) or 1.0
    parity = distribution.get("rate_parity", {}).get("status", "ok")

    if price_action == "raise" and demand_signal in ("low", "very_low"):
        conflicts.append({
            "type": "pricing_vs_demand", "severity": "high",
            "description": "Pricing recomienda subir pero demanda del mercado es baja",
            "resolution_hint": "Mantener precio. Esperar mejora de demanda antes de subir."
        })

    if rep_gri > 85 and your_rank and total and (your_rank / total) > 0.6:
        conflicts.append({
            "type": "reputation_vs_pricing", "severity": "medium",
            "description": f"GRI excelente ({rep_gri}) pero precio en posición débil (#{your_rank}/{total})",
            "resolution_hint": "Reputación justifica subida de precio. Oportunidad."
        })

    if visibility < 0.5 and price_action == "raise":
        conflicts.append({
            "type": "distribution_vs_pricing", "severity": "medium",
            "description": f"Visibilidad baja ({visibility:.2f}) — subir precio puede reducir exposición",
            "resolution_hint": "Mejorar visibilidad primero. Subida de precio después."
        })

    if parity == "violation":
        conflicts.append({
            "type": "rate_parity_violation", "severity": "high",
            "description": "Violación de paridad de tarifas entre canales",
            "resolution_hint": "Resolver paridad antes de cualquier cambio de precio."
        })

    if rep_can_premium and demand_signal in ("low", "very_low"):
        conflicts.append({
            "type": "reputation_vs_demand", "severity": "medium",
            "description": "Reputación permite premium pero demanda baja — subir ahora arriesga ocupación",
            "resolution_hint": "Mantener o subida muy moderada. Priorizar ocupación hasta que demanda repunte."
        })

    return conflicts


def _normalize_opportunity_text(s: str) -> str:
    """Normaliza texto para deduplicar oportunidades."""
    if not s or not isinstance(s, str):
        return ""
    n = CONSOLIDATION_WEIGHTS.get("opportunity_normalize_len", 80)
    return " ".join(s.lower().split())[:n]


def _get_confidence_weights(agent_outputs: dict) -> dict:
    """Extrae los confidence_score de cada agente (con defaults)."""
    pricing = agent_outputs.get("pricing", {})
    demand = agent_outputs.get("demand", {})
    reputation = agent_outputs.get("reputation", {})
    distribution = agent_outputs.get("distribution", {})
    return {
        "compset": agent_outputs.get("compset", {}).get("confidence_score", 0.7),
        "pricing": pricing.get("confidence_score", 0.7),
        "demand": demand.get("confidence_score", 0.65),
        "reputation": reputation.get("confidence_score", 0.75),
        "distribution": distribution.get("confidence_score", 0.65),
    }


def _apply_base_signals(agent_outputs: dict, w: dict) -> dict:
    """Aplica señales base de Pricing y Demand a un dict de señales (raise/hold/lower/promo)."""
    pricing = agent_outputs.get("pricing", {})
    demand = agent_outputs.get("demand", {})
    signals = {"raise": 0.0, "hold": 0.0, "lower": 0.0, "promo": 0.0}
    p_action = pricing.get("recommendation", {}).get("action", "hold")
    d_action = demand.get("price_implication", "hold")
    if p_action in signals:
        signals[p_action] += w["pricing"]
    if d_action in signals:
        signals[d_action] += w["demand"]
    return signals


def _apply_reputation_signals(signals: dict, reputation: dict, w: dict) -> None:
    """Modifica signals in-place según reputación (GRI premium, percepción de precio)."""
    if not reputation:
        return
    gri = reputation.get("gri", {})
    gri_val = gri.get("value") or 0
    can_premium = gri.get("can_command_premium", False)
    premium_pct = gri.get("suggested_premium_pct") or 0
    price_perception = (reputation.get("sentiment_analysis") or {}).get("price_perception", "")
    min_gri = CONSOLIDATION_WEIGHTS.get("gri_min_for_premium", 78)
    if can_premium and premium_pct > 0 and isinstance(gri_val, (int, float)) and gri_val >= min_gri:
        factor = CONSOLIDATION_WEIGHTS.get("reputation_premium_raise_factor", 0.4)
        signals["raise"] += w["reputation"] * factor
    if price_perception and isinstance(price_perception, str) and "caro" in price_perception.lower():
        factor = CONSOLIDATION_WEIGHTS.get("reputation_overprice_lower_factor", 0.3)
        signals["lower"] += w["reputation"] * factor


def _apply_distribution_signals(signals: dict, distribution: dict, p_action: str) -> None:
    """Modifica signals in-place según distribución (paridad, visibilidad)."""
    if not distribution:
        return
    parity_status = distribution.get("rate_parity", {}).get("status", "ok")
    visibility = distribution.get("visibility_score", 1.0) or 1.0
    if parity_status == "violation":
        mult = CONSOLIDATION_WEIGHTS.get("parity_raise_lower_multiplier", 0.3)
        boost = CONSOLIDATION_WEIGHTS.get("parity_hold_boost", 0.8)
        signals["raise"] *= mult
        signals["lower"] *= mult
        signals["hold"] += boost
    if isinstance(visibility, (int, float)) and visibility < 0.5 and p_action == "raise":
        mult = CONSOLIDATION_WEIGHTS.get("visibility_low_raise_multiplier", 0.6)
        boost = CONSOLIDATION_WEIGHTS.get("visibility_low_hold_boost", 0.2)
        signals["raise"] *= mult
        signals["hold"] += boost


def _apply_conflict_penalties(signals: dict, conflicts: list) -> bool:
    """Aplica penalizaciones por conflictos de alta severidad. Devuelve True si hubo alguno."""
    has_high = any(c.get("severity") == "high" for c in conflicts)
    if not has_high:
        return False
    mult = CONSOLIDATION_WEIGHTS.get("high_conflict_raise_multiplier", 0.5)
    boost = CONSOLIDATION_WEIGHTS.get("high_conflict_hold_boost", 0.4)
    signals["raise"] *= mult
    signals["hold"] += boost
    return True


def _final_action_from_signals(signals: dict) -> str:
    """Obtiene la acción final (raise/hold/lower/promo); fallback a hold si empate o cero."""
    action = max(signals, key=signals.get)
    if signals[action] <= 0:
        return "hold"
    return action


def _dedupe_opportunities(agent_outputs: dict) -> list:
    """Extrae y deduplica oportunidades de pricing, demand y distribution."""
    pricing = agent_outputs.get("pricing", {})
    demand = agent_outputs.get("demand", {})
    distribution = agent_outputs.get("distribution", {})
    seen = set()
    out = []
    max_n = CONSOLIDATION_WEIGHTS.get("opportunity_max_count", 5)
    for src in [pricing.get("yield_opportunities", []),
                demand.get("opportunities", []),
                distribution.get("quick_wins", [])]:
        for item in src:
            desc = item.get("description") or item.get("action", "") if isinstance(item, dict) else str(item)
            if not desc:
                continue
            key = _normalize_opportunity_text(desc)
            if key and key not in seen:
                seen.add(key)
                out.append(desc if isinstance(desc, str) else str(desc))
            if len(out) >= max_n:
                return out[:max_n]
    return out[:max_n]


def _build_alerts(agent_outputs: dict) -> list:
    """Construye lista de alertas desde pricing, distribution y reputation."""
    pricing = agent_outputs.get("pricing", {})
    distribution = agent_outputs.get("distribution", {})
    reputation = agent_outputs.get("reputation", {})
    alerts = []
    for alert in pricing.get("pricing_alerts", []):
        if alert.get("level") == "high":
            alerts.append({"level": "high", "source": "pricing",
                           "message": alert.get("description", "")})
    if distribution.get("rate_parity", {}).get("status") == "violation":
        alerts.append({"level": "high", "source": "distribution",
                       "message": "Violación de paridad de tarifas detectada"})
    neg = reputation.get("recent_negative_themes", [])
    if neg:
        alerts.append({"level": "medium", "source": "reputation",
                       "message": f"Temas negativos recurrentes: {', '.join(neg[:3])}"})
    return [a for a in alerts if a.get("message")]


def _build_critical_issues(conflicts: list, alerts: list) -> list:
    """Lista de descripciones de conflictos high y alertas high."""
    out = []
    for c in conflicts:
        if c.get("severity") == "high":
            out.append(c.get("description", c.get("type", "Conflicto crítico")))
    for a in alerts:
        if a.get("level") == "high":
            out.append(a.get("message", "Alerta alta"))
    return out


def _build_signal_sources(p_action: str, d_action: str, w: dict, has_high_conflict: bool) -> list:
    """Lista de frases que explican el origen de las señales."""
    out = [
        f"Pricing: {p_action} (conf {w['pricing']})",
        f"Demand: {d_action} (conf {w['demand']})",
    ]
    if has_high_conflict:
        out.append("Conflictos de alta severidad aplicados → prioridad a hold.")
    return out


def _build_consolidation_rationale(signal_sources: list, final_action: str) -> str:
    """Una sola frase con las fuentes y la decisión."""
    return " ".join(signal_sources) + f" → Decisión: {final_action.upper()}."


def _derive_overall_status(
    critical_issues: list,
    parity_violation: bool,
    has_high_conflict: bool,
    demand_signal: str,
) -> str:
    """
    Deriva overall_status de forma determinista para que el report no invente.
    Valores: alert | needs_attention | stable | strong
    """
    if critical_issues or parity_violation or has_high_conflict:
        if parity_violation or (has_high_conflict and demand_signal in ("low", "very_low")):
            return "alert"
        return "needs_attention"
    if demand_signal in ("high", "very_high"):
        return "strong"
    return "stable"


def _build_severity_summary(conflicts: list, alerts: list) -> dict:
    """Resumen de severidades para trazabilidad."""
    high_conflicts = sum(1 for c in conflicts if c.get("severity") == "high")
    medium_conflicts = sum(1 for c in conflicts if c.get("severity") == "medium")
    high_alerts = sum(1 for a in alerts if a.get("level") == "high")
    medium_alerts = sum(1 for a in alerts if a.get("level") == "medium")
    return {
        "high_conflicts": high_conflicts,
        "medium_conflicts": medium_conflicts,
        "high_alerts": high_alerts,
        "medium_alerts": medium_alerts,
        "has_critical": high_conflicts > 0 or high_alerts > 0,
    }


def _build_decision_drivers(p_action: str, d_action: str, w: dict) -> list:
    """Frases cortas que impulsaron la decisión (sin penalizaciones)."""
    return [
        f"Pricing recomienda {p_action} (confianza {w['pricing']})",
        f"Demand implica {d_action} (confianza {w['demand']})",
    ]


def _build_decision_penalties(
    conflicts: list,
    parity_violation: bool,
    visibility_low: bool,
    p_action: str,
) -> list:
    """Frases que describen penalizaciones o restricciones aplicadas."""
    out = []
    if parity_violation:
        out.append("Paridad violada: prioridad a hold hasta resolver.")
    if visibility_low and p_action == "raise":
        out.append("Visibilidad baja: reduce peso de subida de precio.")
    for c in conflicts:
        if c.get("severity") == "high":
            out.append(c.get("resolution_hint", c.get("description", "")))
    return out


def _build_action_constraints(parity_violation: bool, critical_issues: list) -> list:
    """Restricciones que debe respetar la primera acción (ej. no subir si paridad)."""
    out = []
    if parity_violation:
        out.append("Resolver paridad antes de cualquier cambio de precio.")
    if critical_issues:
        out.append("La acción debe ser coherente con la resolución de conflictos detectados.")
    return out


def _build_recommended_priority_actions_seed(
    consolidated_action: str,
    parity_violation: bool,
    critical_issues: list,
    alerts: list,
) -> list:
    """
    Semilla determinista de acciones prioritarias para el report.
    El LLM debe usarla como base y expandir con detalle; no inventar urgencias opuestas.
    Cada item: { "urgency": "immediate"|"this_week"|"this_month", "reason_source": str, "action_hint": str }
    """
    seed = []
    if parity_violation:
        seed.append({
            "urgency": "immediate",
            "reason_source": "distribution",
            "action_hint": "Resolver violación de paridad de tarifas entre canales.",
        })
    for _ in critical_issues:
        if not any(s.get("reason_source") == "conflict" for s in seed):
            seed.append({
                "urgency": "immediate" if parity_violation else "this_week",
                "reason_source": "conflict",
                "action_hint": "Seguir la decisión consolidada (conflictos resueltos).",
            })
            break
    seed.append({
        "urgency": "this_week",
        "reason_source": "consolidation",
        "action_hint": f"Acción de precio consolidada: {consolidated_action.upper()}.",
    })
    return seed[:3]


def consolidate(agent_outputs: dict, conflicts: list) -> dict:
    """
    Orquesta la consolidación: señales base → reputación → distribución → conflictos
    → decisión final, oportunidades, alertas, rationale, derived_overall_status y seed de acciones.
    """
    pricing = agent_outputs.get("pricing", {})
    demand = agent_outputs.get("demand", {})
    reputation = agent_outputs.get("reputation", {})
    distribution = agent_outputs.get("distribution", {})

    w = _get_confidence_weights(agent_outputs)
    signals = _apply_base_signals(agent_outputs, w)
    p_action = pricing.get("recommendation", {}).get("action", "hold")
    d_action = demand.get("price_implication", "hold")

    _apply_reputation_signals(signals, reputation, w)
    _apply_distribution_signals(signals, distribution, p_action)
    has_high_conflict = _apply_conflict_penalties(signals, conflicts)

    demand_signal = demand.get("demand_index", {}).get("signal", "medium")
    strategy = derive_strategy(agent_outputs, conflicts)
    action_before_strategy = _final_action_from_signals(signals)
    apply_strategy_modulation(
        signals,
        strategy["strategy_label"],
        demand_signal=demand_signal,
        p_action=p_action,
    )
    final_action = _final_action_from_signals(signals)
    strategy_influence_on_decision = build_strategy_influence_on_decision(
        strategy["strategy_label"],
        action_before_strategy,
        final_action,
    )

    opportunities = _dedupe_opportunities(agent_outputs)
    alerts = _build_alerts(agent_outputs)
    critical_issues = _build_critical_issues(conflicts, alerts)
    signal_sources = _build_signal_sources(p_action, d_action, w, has_high_conflict)
    consolidation_rationale = _build_consolidation_rationale(signal_sources, final_action)

    parity_violation = distribution.get("rate_parity", {}).get("status") == "violation"
    derived_overall_status = _derive_overall_status(
        critical_issues, parity_violation, has_high_conflict, demand_signal
    )
    severity_summary = _build_severity_summary(conflicts, alerts)
    decision_drivers = _build_decision_drivers(p_action, d_action, w)
    visibility = distribution.get("visibility_score", 1.0) or 1.0
    visibility_low = isinstance(visibility, (int, float)) and visibility < 0.5
    decision_penalties = _build_decision_penalties(
        conflicts, parity_violation, visibility_low, p_action
    )
    action_constraints = _build_action_constraints(parity_violation, critical_issues)
    recommended_priority_actions_seed = _build_recommended_priority_actions_seed(
        final_action, parity_violation, critical_issues, alerts
    )

    return {
        "consolidated_price_action": final_action,
        "price_signal_weights": signals,
        "opportunities": opportunities,
        "alerts": alerts,
        "conflicts": conflicts,
        "system_confidence": round(sum(w.values()) / len(w), 2),
        "generated_at": datetime.now().isoformat(),
        "consolidation_rationale": consolidation_rationale,
        "critical_issues": critical_issues,
        "signal_sources": signal_sources,
        "derived_overall_status": derived_overall_status,
        "severity_summary": severity_summary,
        "decision_drivers": decision_drivers,
        "decision_penalties": decision_penalties,
        "action_constraints": action_constraints,
        "recommended_priority_actions_seed": recommended_priority_actions_seed,
        "strategy_label": strategy["strategy_label"],
        "strategy_rationale": strategy["strategy_rationale"],
        "strategy_drivers": strategy["strategy_drivers"],
        "strategy_risks": strategy["strategy_risks"],
        "strategy_confidence": strategy["strategy_confidence"],
        "strategy_influence_on_decision": strategy_influence_on_decision,
        "strategy_scorecard": strategy.get("strategy_scorecard", {}),
        "strategy_counter_signals": strategy.get("strategy_counter_signals", []),
        "strategy_confidence_reason": strategy.get("strategy_confidence_reason", ""),
    }


_ORCH_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _save(name: str, data: dict):
    agents_dir = os.path.join(_ORCH_BASE_DIR, "data", "agents")
    os.makedirs(agents_dir, exist_ok=True)
    try:
        path = os.path.join(agents_dir, f"{name}_output.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _noop_progress(stage: str, progress_pct: int) -> None:
    pass


async def run_full_analysis(
    hotel_name: str,
    city_hint: str = "",
    api_key: str = "",
    scraped_data: dict = None,
    market_candidates: dict = None,
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> dict:
    if progress_callback is None:
        progress_callback = _noop_progress

    start = time.time()
    print(f"\n{'='*55}")
    print(f"  RevMax Orchestrator v2  ·  {hotel_name}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*55}\n")

    outputs = {}

    # Fase 1 — Discovery
    print("▶ Fase 1/5 — Discovery")
    progress_callback("discovery", 10)
    outputs["discovery"] = await run_discovery_agent(hotel_name, city_hint, api_key, scraped_data)
    _save("discovery", outputs["discovery"])

    # Fase 2 — Compset
    print("\n▶ Fase 2/5 — Compset")
    progress_callback("compset", 25)
    outputs["compset"] = await run_compset_agent(
        outputs["discovery"], market_candidates or {"candidates": []}, api_key
    )
    _save("compset", outputs["compset"])

    # Fase 3 — Paralelo
    print("\n▶ Fase 3/5 — Paralelo [Pricing · Demand · Reputation · Distribution]")
    progress_callback("parallel", 40)
    demand_stub = {"demand_index": {"signal": "medium", "score": 55}, "events_detected": []}

    results = await asyncio.gather(
        run_pricing_agent(outputs["discovery"], outputs["compset"], demand_stub, api_key),
        run_demand_agent(outputs["discovery"], outputs["compset"], api_key),
        run_reputation_agent(outputs["discovery"], outputs["compset"], api_key),
        run_distribution_agent(outputs["discovery"], outputs["compset"], api_key),
        return_exceptions=True
    )

    keys = ["pricing", "demand", "reputation", "distribution"]
    for idx, (key, result) in enumerate(zip(keys, results)):
        outputs[key] = result if not isinstance(result, Exception) \
            else {"error": str(result), "confidence_score": 0.3}
        _save(key, outputs[key])
        progress_callback(key, 40 + (idx + 1) * 2)

    print(f"  ✓ Pricing  ·  ✓ Demand  ·  ✓ Reputation  ·  ✓ Distribution")

    # Fase 4 — Consolidar
    print("\n▶ Fase 4/5 — Consolidando")
    progress_callback("consolidate", 60)
    conflicts = detect_conflicts(outputs)
    for c in conflicts:
        print(f"  ! [{c['severity'].upper()}] {c['description']}")
    briefing = consolidate(outputs, conflicts)
    engine_alerts = detect_alerts(outputs, conflicts, briefing)
    briefing["alerts"] = engine_alerts
    briefing["alert_summary"] = build_alert_summary(engine_alerts)
    briefing["alert_high_count"] = count_alert_severity(engine_alerts, "high")
    briefing["alert_critical_count"] = count_alert_severity(engine_alerts, "critical")
    if engine_alerts:
        for a in engine_alerts:
            if a.get("severity") in ("high", "critical"):
                print(f"  ⚠ [{a.get('severity', '?').upper()}] {a.get('type', '?')}: {a.get('message', '')[:60]}")
    market_signals = detect_market_signals(outputs, conflicts, briefing)
    briefing["market_signals"] = market_signals
    briefing["market_signal_summary"] = build_market_signal_summary(market_signals)
    briefing["market_raise_signal_count"] = count_market_signals_by_effect(market_signals, "raise")
    briefing["market_lower_signal_count"] = count_market_signals_by_effect(market_signals, "lower")
    briefing["market_caution_signal_count"] = count_market_signals_by_effect(market_signals, "caution")
    recommended_actions = build_recommended_actions(outputs, conflicts, briefing)
    briefing["recommended_actions"] = recommended_actions
    briefing["recommended_action_summary"] = build_recommended_action_summary(recommended_actions)
    briefing["urgent_action_count"] = count_actions_by_priority(recommended_actions, "urgent")
    briefing["high_priority_action_count"] = count_actions_by_priority(recommended_actions, "high")
    briefing["recommended_priority_actions_seed"] = [
        {
            "urgency": a.get("horizon", "this_week"),
            "reason_source": ", ".join(a.get("source_signals", [])),
            "action_hint": f"{a.get('title', '')} — {a.get('rationale', '')}",
        }
        for a in recommended_actions
    ]
    print(f"  Acción: {briefing['consolidated_price_action'].upper()} · Estado: {briefing.get('derived_overall_status', '?')} · Estrategia: {briefing.get('strategy_label', '?')} · Acciones: {len(recommended_actions)}")

    full_analysis = {
        "hotel_name": hotel_name,
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "agent_outputs": outputs,
        "briefing": briefing,
    }

    # Fase 5 — Report Writer
    print("\n▶ Fase 5/5 — Report Writer")
    progress_callback("report", 75)
    report = await run_report_agent(full_analysis, api_key)
    _save("report", report)
    full_analysis["report"] = report
    progress_callback("report", 85)

    elapsed = round(time.time() - start, 1)
    full_analysis["elapsed_seconds"] = elapsed
    _save("full_analysis", full_analysis)

    print(f"\n{'='*55}")
    print(f"  ✓ Completado en {elapsed}s")
    print(f"  Estado: {report.get('overall_status','?').upper()}")
    print(f"  Asunto: {report.get('email_subject','?')}")
    print(f"{'='*55}\n")

    return full_analysis


async def run_fast_demo(
    hotel_name: str,
    city_hint: str = "",
    api_key: str = "",
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> dict:
    """
    Demo rápido (~15-25s): stubs de todos los agentes + solo el agente de informe.
    """
    if progress_callback is None:
        progress_callback = _noop_progress
    start = time.time()
    progress_callback("report", 20)
    outputs = {
        "discovery": {
            "hotel_name": hotel_name,
            "city": city_hint or "Ciudad",
            "found": True,
            "confidence_score": 0.9,
        },
        "compset": {
            "candidates": [],
            "your_position_rank": 3,
            "total_compset": 8,
            "confidence_score": 0.7,
        },
        "pricing": {
            "recommendation": {"action": "hold"},
            "market_context": {"your_position_rank": 3, "total_compset": 8},
            "confidence_score": 0.7,
        },
        "demand": {
            "demand_index": {"signal": "medium", "score": 55},
            "price_implication": "hold",
            "confidence_score": 0.65,
        },
        "reputation": {
            "gri": {"value": 78},
            "confidence_score": 0.75,
        },
        "distribution": {
            "visibility_score": 0.8,
            "rate_parity": {"status": "ok"},
            "confidence_score": 0.65,
        },
    }
    conflicts = detect_conflicts(outputs)
    briefing = consolidate(outputs, conflicts)
    engine_alerts = detect_alerts(outputs, conflicts, briefing)
    briefing["alerts"] = engine_alerts
    briefing["alert_summary"] = build_alert_summary(engine_alerts)
    briefing["alert_high_count"] = count_alert_severity(engine_alerts, "high")
    briefing["alert_critical_count"] = count_alert_severity(engine_alerts, "critical")
    market_signals = detect_market_signals(outputs, conflicts, briefing)
    briefing["market_signals"] = market_signals
    briefing["market_signal_summary"] = build_market_signal_summary(market_signals)
    briefing["market_raise_signal_count"] = count_market_signals_by_effect(market_signals, "raise")
    briefing["market_lower_signal_count"] = count_market_signals_by_effect(market_signals, "lower")
    briefing["market_caution_signal_count"] = count_market_signals_by_effect(market_signals, "caution")
    recommended_actions = build_recommended_actions(outputs, conflicts, briefing)
    briefing["recommended_actions"] = recommended_actions
    briefing["recommended_action_summary"] = build_recommended_action_summary(recommended_actions)
    briefing["urgent_action_count"] = count_actions_by_priority(recommended_actions, "urgent")
    briefing["high_priority_action_count"] = count_actions_by_priority(recommended_actions, "high")
    briefing["recommended_priority_actions_seed"] = [
        {
            "urgency": a.get("horizon", "this_week"),
            "reason_source": ", ".join(a.get("source_signals", [])),
            "action_hint": f"{a.get('title', '')} — {a.get('rationale', '')}",
        }
        for a in recommended_actions
    ]
    full_analysis = {
        "hotel_name": hotel_name,
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "agent_outputs": outputs,
        "briefing": briefing,
    }
    progress_callback("report", 70)
    report = await run_report_agent(full_analysis, api_key)
    full_analysis["report"] = report
    full_analysis["elapsed_seconds"] = round(time.time() - start, 1)
    progress_callback("report", 85)
    return full_analysis


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--hotel", default="")
    parser.add_argument("--city", default="")
    parser.add_argument("--config", default="config.json")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key and os.path.exists(args.config):
        with open(args.config) as f:
            api_key = json.load(f).get("anthropic_api_key", "")

    if not api_key:
        print("ERROR: define ANTHROPIC_API_KEY")
        sys.exit(1)

    hotel = args.hotel or input("Nombre del hotel: ").strip()
    city = args.city or input("Ciudad (Enter para omitir): ").strip()

    result = asyncio.run(run_full_analysis(hotel, city, api_key))
    report = result.get("report", {})

    print("ACCIONES PRIORITARIAS:")
    for a in report.get("priority_actions", []):
        icon = "🔴" if a.get("urgency") == "immediate" else "🟡"
        print(f"  {icon} {a.get('rank')}. {a.get('action')}")
        print(f"     → {a.get('reason')}")

    watchlist = report.get("weekly_watchlist")
    if watchlist:
        print(f"\n📌 ESTA SEMANA: {watchlist}")
