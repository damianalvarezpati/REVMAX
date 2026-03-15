# FASE 11 — Impact Engine

## 1. PROBLEMA QUE RESUELVE IMPACT ENGINE

RevMax ya produce **alerts**, **market_signals**, **recommended_actions**, **opportunities** y **notifications**, pero **no estimaba**:

- valor potencial de una oportunidad  
- impacto esperado de una acción  
- prioridad económica relativa  

El **Impact Engine** añade una capa de **estimación heurística** (no forecasting ni ML) para que RevMax no solo diga **qué hacer**, sino también **cuánto valor potencial** podría capturarse o protegerse, permitiendo priorizar decisiones con criterio económico.

---

## 2. ARCHIVOS MODIFICADOS

| Archivo | Acción |
|---------|--------|
| `impact_engine.py` | **Creado** — motor de estimación de impacto |
| `orchestrator.py` | **Modificado** — integración del engine tras Opportunity Engine |
| `agents/agent_07_report.py` | **Modificado** — citar impacto estimado en el informe |
| `tests/test_impact_engine.py` | **Creado** — tests unitarios del engine |
| `FASE_11_IMPACT_ENGINE.md` | **Creado** — esta documentación |

**No tocados:** `job_schema.py`, `job_state.py`, `job_runtime.py`, `job_watchdog.py`, `job_recovery.py`, `job_observability.py`, `admin_panel.py`, `analysis_runner.py`.  
**No rotos:** `consolidate()`, Strategy Engine, Alert Engine, Market Signals, Decision Engine / Action Planner, Notification Logic, Intelligence Memory, Opportunity Engine, Executive Output Layer, tests existentes.

---

## 3. CAMBIOS IMPLEMENTADOS

- **impact_engine.py**  
  - `_get_context(briefing)`: extrae demanda, GRI, ranking, alertas críticas, estrategia y tipos de señales del briefing.  
  - `_estimate_opportunity_impact(opp, ctx)`: por tipo de oportunidad (PRICE_CAPTURE, UNDERVALUATION, VISIBILITY_RECOVERY, DEMAND_RECOVERY, DEFENSIVE_STABILIZATION) asigna `impact_estimate`, `impact_confidence`, `impact_reason`.  
  - `_estimate_action_impact(action, ctx)`: por tipo de acción (FIX_PARITY, PRICE_INCREASE, PRICE_DECREASE, HOLD_PRICE, IMPROVE_VISIBILITY, PROTECT_RATE, MONITOR_DEMAND, REVIEW_POSITIONING) asigna `action_impact_estimate`, `action_impact_confidence`.  
  - `_build_impact_summary(...)`, `_pick_top_value_opportunity(...)`.  
  - `build_impact_estimates(briefing)` devuelve: `opportunity_impacts`, `action_impacts`, `impact_summary`, `top_value_opportunity`.

- **orchestrator.py**  
  - Tras Opportunity Engine se rellenan en el briefing: `demand_score`, `demand_signal`, `gri_value`, `your_rank`, `total_compset` desde `outputs` (demand, pricing, reputation).  
  - Se llama `impact_results = build_impact_estimates(briefing)`.  
  - Se actualiza el briefing: `opportunities` ← `opportunity_impacts`, `recommended_actions` ← `action_impacts`, y se añaden `impact_summary`, `top_value_opportunity`.  
  - Integración idéntica en `run_full_analysis` y `run_fast_demo`.

- **agents/agent_07_report.py**  
  - Se leen `impact_summary` y `top_value_opportunity` del briefing.  
  - En el prompt se incluyen: `impact_summary`, `top_value_opportunity`, y en la lista de oportunidades `impact_estimate`, `impact_confidence`, `impact_reason` (fallback: "impact uncertain" / "low").  
  - En la lista de acciones: `action_impact_estimate`, `action_impact_confidence` (fallback: "impact uncertain" / "low").  
  - Regla IMPACTO: usar solo impactos generados por código; no inventar; si no hay estimación clara, indicar "impact uncertain".

- **tests/test_impact_engine.py**  
  - Tests: impact for price capture opportunity, undervaluation, visibility recovery, demand recovery, impact summary exists, no crash if briefing vacío, action impacts con estimate/confidence, top_value_opportunity cuando hay oportunidades.

---

## 4. CÓDIGO COMPLETO

### impact_engine.py

```python
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
```

### orchestrator.py (fragmentos relevantes)

- Import: `from impact_engine import build_impact_estimates`
- Tras Opportunity Engine y antes de `build_executive_briefing` (en `run_full_analysis` y `run_fast_demo`):

```python
    demand = outputs.get("demand", {})
    pricing = outputs.get("pricing", {})
    reputation = outputs.get("reputation", {})
    briefing["demand_score"] = (demand.get("demand_index") or {}).get("score", 50)
    briefing["demand_signal"] = (demand.get("demand_index") or {}).get("signal", "medium")
    briefing["gri_value"] = (reputation.get("gri") or {}).get("value") or 0
    briefing["your_rank"] = (pricing.get("market_context") or {}).get("your_position_rank")
    briefing["total_compset"] = (pricing.get("market_context") or {}).get("total_compset", 10)
    impact_results = build_impact_estimates(briefing)
    briefing["opportunities"] = impact_results["opportunity_impacts"]
    briefing["recommended_actions"] = impact_results["action_impacts"]
    briefing["impact_summary"] = impact_results["impact_summary"]
    briefing["top_value_opportunity"] = impact_results["top_value_opportunity"]
```

### agents/agent_07_report.py (fragmentos relevantes)

- Lectura del briefing: `impact_summary = briefing.get("impact_summary", "")`, `top_value_opportunity = briefing.get("top_value_opportunity")`.
- En el prompt: sección con `impact_summary`, `top_value_opportunity`, lista de oportunidades con `impact_estimate`, `impact_confidence`, `impact_reason`, lista de acciones con `action_impact_estimate`, `action_impact_confidence`.
- Regla: "IMPACTO: Para oportunidades y acciones usa SOLO los impact_estimate, impact_confidence, impact_reason y action_impact_estimate, action_impact_confidence generados por código. No inventes cifras ni rangos. Si no hay estimación clara, indica 'impact uncertain'. Ejemplo: 'Opportunity to capture additional ADR. Estimated impact: ADR upside potential +5–9%. Confidence: medium.'"

### tests/test_impact_engine.py

Ver archivo `tests/test_impact_engine.py` en el repositorio: 8 tests (price capture, undervaluation, visibility recovery, demand recovery, impact summary exists, no crash if briefing vacío, action impacts con estimate/confidence, top_value_opportunity cuando hay oportunidades).

---

## 5. EJEMPLOS DE IMPACT ESTIMATION

| Tipo | Condiciones | impact_estimate | impact_confidence |
|------|-------------|-----------------|-------------------|
| PRICE_CAPTURE_OPPORTUNITY | demand_score > 65 + UNDERPRICED_RELATIVE_TO_POSITION | ADR capture potential estimated between +5% and +10% | medium |
| PRICE_CAPTURE_OPPORTUNITY | demand_score > 55 | ADR upside potential: +3% to +7% | low |
| UNDERVALUATION_OPPORTUNITY | gri ≥ 78, rank_ratio ≥ 0.5 | Potential ADR capture through positioning improvement | medium |
| UNDERVALUATION_OPPORTUNITY | resto | Idem | low |
| VISIBILITY_RECOVERY_OPPORTUNITY | — | Improved OTA visibility may unlock additional demand | medium |
| DEMAND_RECOVERY_OPPORTUNITY | — | Occupancy protection potential if pricing aligns with demand | medium |
| DEFENSIVE_STABILIZATION_OPPORTUNITY | has_critical_alerts | Revenue protection by avoiding aggressive pricing | high |
| DEFENSIVE_STABILIZATION_OPPORTUNITY | resto | Idem | medium |
| FIX_PARITY | — | Restore channel consistency; avoid contract and commission risk | high |
| PRICE_INCREASE | demand_score > 65 | ADR upside potential +5% to +9% if demand holds | medium |
| PRICE_INCREASE | resto | Moderate ADR upside; monitor occupancy | low |

---

## 6. LÍMITES DEL SISTEMA

- **No es forecasting real:** las cifras (+5%–+10%, etc.) son rangos heurísticos fijos, no salidas de un modelo predictivo.
- **No hay ML ni simulación de revenue:** solo reglas por tipo de oportunidad/acción y contexto (demanda, GRI, ranking, señales, alertas).
- **No se usan elasticidades ni integración PMS:** la prioridad económica es relativa y cualitativa (low/medium/high confidence).
- **Tipos no mapeados:** oportunidades o acciones de tipo desconocido reciben "Impact uncertain" y confidence "low".
- **Dependencia del briefing:** si `demand_score`, `gri_value`, `your_rank`, `total_compset` no se rellenan en el orchestrator, el engine usa valores por defecto (p. ej. demand_score 50, rank_ratio 0.5).
