"""
RevMax — Orquestador Principal v2
====================================
Pipeline completo con los 7 agentes reales.
Agentes 3–6 corren en paralelo con asyncio.gather().
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
    return " ".join(s.lower().split())[:80]


def consolidate(agent_outputs: dict, conflicts: list) -> dict:
    pricing = agent_outputs.get("pricing", {})
    demand = agent_outputs.get("demand", {})
    reputation = agent_outputs.get("reputation", {})
    distribution = agent_outputs.get("distribution", {})

    w = {
        "compset":      agent_outputs.get("compset", {}).get("confidence_score", 0.7),
        "pricing":      pricing.get("confidence_score", 0.7),
        "demand":       demand.get("confidence_score", 0.65),
        "reputation":   reputation.get("confidence_score", 0.75),
        "distribution": distribution.get("confidence_score", 0.65),
    }

    signals = {"raise": 0.0, "hold": 0.0, "lower": 0.0, "promo": 0.0}
    p_action = pricing.get("recommendation", {}).get("action", "hold")
    d_action = demand.get("price_implication", "hold")
    if p_action in signals:
        signals[p_action] += w["pricing"]
    if d_action in signals:
        signals[d_action] += w["demand"]

    gri = reputation.get("gri", {})
    gri_val = gri.get("value") or 0
    can_premium = gri.get("can_command_premium", False)
    premium_pct = gri.get("suggested_premium_pct") or 0
    price_perception = (reputation.get("sentiment_analysis") or {}).get("price_perception", "")
    if can_premium and premium_pct > 0 and isinstance(gri_val, (int, float)) and gri_val >= 78:
        signals["raise"] += w["reputation"] * 0.4
    if price_perception and isinstance(price_perception, str) and "caro" in price_perception.lower():
        signals["lower"] += w["reputation"] * 0.3

    parity_status = distribution.get("rate_parity", {}).get("status", "ok")
    visibility = distribution.get("visibility_score", 1.0) or 1.0
    if parity_status == "violation":
        signals["raise"] *= 0.3
        signals["lower"] *= 0.3
        signals["hold"] += 0.8
    if isinstance(visibility, (int, float)) and visibility < 0.5 and p_action == "raise":
        signals["raise"] *= 0.6
        signals["hold"] += 0.2

    has_high_conflict = any(c.get("severity") == "high" for c in conflicts)
    if has_high_conflict:
        signals["raise"] *= 0.5
        signals["hold"] += 0.4

    final_action = max(signals, key=signals.get)
    if signals[final_action] <= 0:
        final_action = "hold"

    seen_opp = set()
    opportunities = []
    for src in [pricing.get("yield_opportunities", []),
                demand.get("opportunities", []),
                distribution.get("quick_wins", [])]:
        for item in src:
            desc = item.get("description") or item.get("action", "") if isinstance(item, dict) else str(item)
            if not desc:
                continue
            key = _normalize_opportunity_text(desc)
            if key and key not in seen_opp:
                seen_opp.add(key)
                opportunities.append(desc if isinstance(desc, str) else str(desc))
            if len(opportunities) >= 5:
                break
        if len(opportunities) >= 5:
            break
    opportunities = opportunities[:5]

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
    alerts = [a for a in alerts if a.get("message")]

    critical_issues = []
    for c in conflicts:
        if c.get("severity") == "high":
            critical_issues.append(c.get("description", c.get("type", "Conflicto crítico")))
    for a in alerts:
        if a.get("level") == "high":
            critical_issues.append(a.get("message", "Alerta alta"))

    signal_sources = [
        f"Pricing: {p_action} (conf {w['pricing']})",
        f"Demand: {d_action} (conf {w['demand']})",
    ]
    if has_high_conflict:
        signal_sources.append("Conflictos de alta severidad aplicados → prioridad a hold.")
    consolidation_rationale = " ".join(signal_sources) + f" → Decisión: {final_action.upper()}."

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

    # Fase 3 — Paralelo (progreso por agente: pricing 42, demand 44, reputation 46, distribution 50)
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
    print(f"  Acción: {briefing['consolidated_price_action'].upper()} · Confidence: {briefing['system_confidence']}")

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
    Útil para probar la UI y el email sin esperar el pipeline completo.
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
