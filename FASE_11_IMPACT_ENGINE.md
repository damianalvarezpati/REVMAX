# FASE 11 — Impact Engine

## 1. PROBLEMA QUE RESUELVE IMPACT ENGINE (Y AJUSTE ARQUITECTÓNICO)

RevMax ya produce **alerts**, **market_signals**, **recommended_actions**, **opportunities** y **notifications**, pero **no estimaba** valor potencial de oportunidades, impacto esperado de acciones ni prioridad económica relativa. El **Impact Engine** añade una capa de **estimación heurística** (no forecasting ni ML) para priorizar decisiones.

**Ajuste de consistencia:** El Impact Engine **no sobrescribe** `opportunities` ni `recommended_actions`. Opportunity Engine sigue siendo responsable de `opportunities`, Decision Engine de `recommended_actions`. El Impact Engine genera **estructuras explícitas**: `impact_opportunities` e `impact_actions`, de modo que la trazabilidad conceptual se mantiene y cada engine conserva su responsabilidad.

---

## 2. ARCHIVOS MODIFICADOS

| Archivo | Acción |
|---------|--------|
| `impact_engine.py` | **Creado** — motor de estimación; devuelve `impact_opportunities`, `impact_actions`, `impact_summary`, `top_value_opportunity` |
| `orchestrator.py` | **Modificado** — tras Impact Engine solo `briefing.update(impact_results)`; no sobrescribe `opportunities` ni `recommended_actions` |
| `agents/agent_07_report.py` | **Modificado** — usa `impact_opportunities` e `impact_actions` para mostrar impacto en el informe |
| `tests/test_impact_engine.py` | **Creado/actualizado** — tests del engine y de que originals no se modifican |
| `FASE_11_IMPACT_ENGINE.md` | **Creado/actualizado** — documentación |

**No tocados:** `job_schema.py`, `job_state.py`, `job_runtime.py`, `job_watchdog.py`, `job_recovery.py`, `job_observability.py`, `admin_panel.py`, `analysis_runner.py`.  
**No rotos:** `consolidate()`, Strategy Engine, Alert Engine, Market Signals, Decision Engine, Notification Logic, Intelligence Memory, Opportunity Engine, Executive Output Layer, tests existentes.

---

## 3. CAMBIOS IMPLEMENTADOS

- **impact_engine.py**  
  - `_get_context(briefing)`: extrae demanda, GRI, ranking, alertas críticas, estrategia y tipos de señales.  
  - `_estimate_opportunity_impact(opp, ctx)`: asigna `impact_estimate`, `impact_confidence`, `impact_reason` por tipo de oportunidad.  
  - `_estimate_action_impact(action, ctx)`: asigna `action_impact_estimate`, `action_impact_confidence` por tipo de acción.  
  - `_build_impact_summary(...)`, `_pick_top_value_opportunity(...)`.  
  - `build_impact_estimates(briefing)` **devuelve**: `impact_opportunities`, `impact_actions`, `impact_summary`, `top_value_opportunity`. No modifica `briefing["opportunities"]` ni `briefing["recommended_actions"]`.

- **orchestrator.py**  
  - Tras Opportunity Engine se rellenan `demand_score`, `demand_signal`, `gri_value`, `your_rank`, `total_compset`.  
  - `impact_results = build_impact_estimates(briefing)`; **solo** `briefing.update(impact_results)`. No se sobrescriben `opportunities` ni `recommended_actions`.  
  - Integración idéntica en `run_full_analysis` y `run_fast_demo`.

- **agents/agent_07_report.py**  
  - Se leen `impact_summary`, `top_value_opportunity`, `impact_opportunities`, `impact_actions`.  
  - En el prompt: lista de oportunidades (estructura) y **impact_opportunities** (impact_estimate, impact_confidence, impact_reason); lista de acciones (estructura) y **impact_actions** (action_impact_estimate, action_impact_confidence).  
  - Regla IMPACTO: usar solo `impact_opportunities` e `impact_actions`; no inventar; si no hay estimación clara, "Estimated impact: impact uncertain."; tono ejecutivo y no repetir texto.

- **tests/test_impact_engine.py**  
  - Tests: impact_opportunities existe, impact_actions existe, impact_summary existe, top_value_opportunity existe, oportunidades originales no se modifican, acciones originales no se modifican, no crash si briefing vacío.

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


def _build_impact_summary(impact_opportunities: list, impact_actions: list) -> str:
    """Una frase resumen del impacto estimado."""
    if not impact_opportunities and not impact_actions:
        return "No impact estimates generated for this run."
    parts = []
    high_opps = [o for o in impact_opportunities if o.get("opportunity_level") == "high"]
    if high_opps:
        parts.append(f"{len(high_opps)} high-value opportunity(ies) with impact estimates.")
    if impact_actions:
        parts.append(f"{len(impact_actions)} action(s) with impact estimates.")
    return " ".join(parts) if parts else "Impact estimates attached to opportunities and actions."


def _pick_top_value_opportunity(impact_opportunities: list) -> Optional[dict]:
    """Devuelve la oportunidad de mayor valor percibido (high level primero, luego por confidence)."""
    if not impact_opportunities:
        return None
    conf_order = {"high": 3, "medium": 2, "low": 1}
    level_order = {"high": 3, "medium": 2, "low": 1}
    sorted_opps = sorted(
        impact_opportunities,
        key=lambda o: (
            -level_order.get(o.get("opportunity_level"), 0),
            -conf_order.get(o.get("impact_confidence"), 0),
        ),
    )
    return sorted_opps[0]


def build_impact_estimates(briefing: dict) -> dict:
    """
    Analiza opportunities, recommended_actions, market_signals, demanda, GRI, ranking y estrategia
    del briefing. No modifica briefing["opportunities"] ni briefing["recommended_actions"].
    Devuelve impact_opportunities, impact_actions, impact_summary y top_value_opportunity.
    """
    ctx = _get_context(briefing)
    opportunities = briefing.get("opportunities", [])
    recommended_actions = briefing.get("recommended_actions", [])

    impact_opportunities = [_estimate_opportunity_impact(o, ctx) for o in opportunities]
    impact_actions = [_estimate_action_impact(a, ctx) for a in recommended_actions]

    impact_summary = _build_impact_summary(impact_opportunities, impact_actions)
    top_value_opportunity = _pick_top_value_opportunity(impact_opportunities)

    return {
        "impact_opportunities": impact_opportunities,
        "impact_actions": impact_actions,
        "impact_summary": impact_summary,
        "top_value_opportunity": top_value_opportunity,
    }
```

### orchestrator.py (fragmentos relevantes)

- Import: `from impact_engine import build_impact_estimates`
- Tras Opportunity Engine y antes de `build_executive_briefing` (en `run_full_analysis` y `run_fast_demo`): se rellenan `demand_score`, `demand_signal`, `gri_value`, `your_rank`, `total_compset`; luego:

```python
    impact_results = build_impact_estimates(briefing)
    briefing.update(impact_results)
```

No se sobrescriben `opportunities` ni `recommended_actions`.

### agents/agent_07_report.py (fragmentos relevantes)

- Lectura: `impact_summary`, `top_value_opportunity`, `impact_opportunities`, `impact_actions`.
- En el prompt: lista de oportunidades (estructura) y bloque **IMPACTO POR OPORTUNIDAD** con `impact_opportunities` (type, title, summary, impact_estimate, impact_confidence, impact_reason); lista de acciones (estructura) y bloque **IMPACTO POR ACCIÓN** con `impact_actions` (type, title, action_impact_estimate, action_impact_confidence).
- Regla: "IMPACTO: Usa SOLO impact_opportunities e impact_actions (listas anteriores) para mostrar impacto. No inventes cifras ni rangos. Si no hay estimación clara, indica 'Estimated impact: impact uncertain.' Ejemplo: 'Opportunity to capture additional ADR. Estimated impact: ADR upside potential +5–9%. Confidence: medium.' Mantén tono ejecutivo y no repitas el mismo texto entre secciones."

### tests/test_impact_engine.py

Ver archivo `tests/test_impact_engine.py`: impact_opportunities existe, impact_actions existe, impact_summary existe, top_value_opportunity existe, oportunidades originales no se modifican, acciones originales no se modifican, no crash si briefing vacío.

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
