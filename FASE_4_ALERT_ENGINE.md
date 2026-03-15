# Fase 4 — Alert Engine

---

## 1. PROBLEMA QUE RESUELVE ALERT ENGINE

Antes de la Fase 4, las “alertas” en el sistema eran listas heterogéneas construidas en la consolidación (pricing_alerts, paridad, temas negativos de reputación), sin tipos fijos ni severidades. No existía un motor dedicado que:

- Detectara de forma estructurada situaciones que un director debe conocer de inmediato (paridad, visibilidad, colapso de demanda, conflicto precio/demanda, desajuste reputación/precio, infravaloración).
- Asignara severidad (info, warning, high, critical) para priorizar.
- Garantizara que las alertas llegaran al briefing, al prompt del report y al informe final sin depender del LLM para generarlas.

El Alert Engine centraliza la detección en código, con tipos y severidades definidos, y las integra en el pipeline para que el report las mencione y priorice en las acciones.

---

## 2. ARCHIVOS MODIFICADOS

- **alerts_engine.py** (nuevo): módulo con `detect_alerts(agent_outputs, conflicts, consolidation_result)`, `build_alert_summary(alerts)`, `count_alert_severity(alerts, severity)`, `ALERT_CONFIG` y `ALERT_SEVERITIES`.
- **orchestrator.py**: import de `detect_alerts`, `build_alert_summary`, `count_alert_severity`; después de `consolidate()` en `run_full_analysis` y en `run_fast_demo`: llamada a `detect_alerts`, asignación en el briefing de `alerts`, `alert_summary`, `alert_high_count`, `alert_critical_count`, y log de alertas high/critical.
- **agents/agent_07_report.py**: lectura de `alert_summary`, `alert_high_count`, `alert_critical_count` del briefing; sección "ALERTAS DETECTADAS POR REVMAX" en el prompt con lista formateada (severity, type, source, message); regla ALERTAS: mencionar en report_text si hay high/critical, priorizar alertas críticas en priority_actions, overall_status al menos needs_attention/alert si hay alert_critical_count > 0.
- **tests/test_alerts.py** (nuevo): tests para parity critical, low visibility warning, demand collapse high, price_too_high_for_demand, strong_undervalue, reputation_price_mismatch, alert_summary/counts, ALERT_CONFIG.

---

## 3. CAMBIOS IMPLEMENTADOS

- **Tipos de alerta:** PARITY_VIOLATION (critical), LOW_VISIBILITY (warning), DEMAND_COLLAPSE (high), PRICE_TOO_HIGH_FOR_DEMAND (high), REPUTATION_PRICE_MISMATCH (warning), STRONG_UNDERVALUE (warning). Cada una con `type`, `severity`, `message`, `source`.
- **Umbrales en ALERT_CONFIG:** visibility_low_threshold 0.5, demand_collapse_score_max 35, strong_reputation_gri_min 82, undervalue_rank_ratio_min 0.5.
- **Orchestrator:** Tras `briefing = consolidate(...)` se llama `detect_alerts(outputs, conflicts, briefing)` y se actualiza el briefing con los cuatro campos; en consola se imprimen las alertas high/critical.
- **Report:** El prompt incluye la sección de alertas con summary, counts y lista; la regla ALERTAS obliga a citar alertas high/critical en report_text, a priorizar críticas en priority_actions y a no usar stable/strong en overall_status si hay alertas críticas.

---

## 4. CÓDIGO COMPLETO

### alerts_engine.py

```python
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
```

### Cambios en orchestrator.py

**Import (junto a los de strategy_engine):**
```python
from alerts_engine import detect_alerts, build_alert_summary, count_alert_severity
```

**Tras `briefing = consolidate(outputs, conflicts)` en run_full_analysis:**
```python
    engine_alerts = detect_alerts(outputs, conflicts, briefing)
    briefing["alerts"] = engine_alerts
    briefing["alert_summary"] = build_alert_summary(engine_alerts)
    briefing["alert_high_count"] = count_alert_severity(engine_alerts, "high")
    briefing["alert_critical_count"] = count_alert_severity(engine_alerts, "critical")
    if engine_alerts:
        for a in engine_alerts:
            if a.get("severity") in ("high", "critical"):
                print(f"  ⚠ [{a.get('severity', '?').upper()}] {a.get('type', '?')}: {a.get('message', '')[:60]}")
```

**Lo mismo tras `briefing = consolidate(outputs, conflicts)` en run_fast_demo:**
```python
    engine_alerts = detect_alerts(outputs, conflicts, briefing)
    briefing["alerts"] = engine_alerts
    briefing["alert_summary"] = build_alert_summary(engine_alerts)
    briefing["alert_high_count"] = count_alert_severity(engine_alerts, "high")
    briefing["alert_critical_count"] = count_alert_severity(engine_alerts, "critical")
```

### Cambios en agents/agent_07_report.py

**Variables del briefing (junto a strategy_confidence_reason):**
```python
    alert_summary = briefing.get("alert_summary", "")
    alert_high_count = briefing.get("alert_high_count", 0)
    alert_critical_count = briefing.get("alert_critical_count", 0)
```

**Sustitución del bloque ALERTAS por:**
```python
ALERTAS DETECTADAS POR REVMAX (generadas por código; si hay high o critical deben aparecer en el informe):
  alert_summary: {alert_summary or 'Ninguna.'}
  alert_high_count: {alert_high_count}
  alert_critical_count: {alert_critical_count}
  Lista de alertas:
{chr(10).join(f'  [{a.get("severity","?").upper()}] {a.get("type","?")} ({a.get("source","?")}): {a.get("message","?")}' for a in alerts) if alerts else '  Ninguna.'}
```

**Nueva regla antes de "Genera el informe siguiendo EXACTAMENTE...":**
```python
- ALERTAS: Si hay alertas de severidad high o critical (alert_high_count: {alert_high_count}, alert_critical_count: {alert_critical_count}), debes mencionarlas en report_text en una frase clara (ej. "RevMax detecta X alerta(s) crítica(s): paridad de tarifas; resolver antes de cambiar precios"). Las priority_actions deben priorizar las alertas críticas (ej. si hay PARITY_VIOLATION, la primera acción debe ser resolver paridad). Si alert_critical_count > 0, overall_status debe ser al menos "needs_attention" o "alert"; no uses "stable" o "strong" si hay alertas críticas.
```

### tests/test_alerts.py

(Contenido completo del archivo tal como está en el workspace: 8 tests con _base_outputs, _briefing_stub, test_parity_violation_critical_alert, test_low_visibility_warning, test_demand_collapse_high, test_price_too_high_for_demand, test_strong_undervalue, test_alert_summary_and_counts, test_reputation_price_mismatch, test_alert_config_defined.)

---

## 5. EJEMPLOS REALES DE ALERTAS

- **PARITY_VIOLATION (critical):** `distribution.rate_parity.status == "violation"` → type PARITY_VIOLATION, severity critical, message "Hotel appears cheaper on OTA than direct channel. Resolve rate parity before any price change.", source distribution.

- **LOW_VISIBILITY (warning):** `visibility_score == 0.35` → type LOW_VISIBILITY, severity warning, message "Visibility score (0.35) is below threshold. Consider improving OTA presence before raising prices.", source distribution.

- **DEMAND_COLLAPSE (high):** `demand_index.score == 28` → type DEMAND_COLLAPSE, severity high, message "Demand index very low (score 28). Prioritise occupancy; avoid aggressive price increases.", source demand.

- **PRICE_TOO_HIGH_FOR_DEMAND (high):** pricing action raise y demand_signal low → type PRICE_TOO_HIGH_FOR_DEMAND, severity high, message "Pricing recommends raise but demand is low. Consolidation favours hold; do not raise until demand improves.", source pricing.

- **STRONG_UNDERVALUE (warning):** GRI 85, rank 6/8 → type STRONG_UNDERVALUE, severity warning, message "Strong reputation (GRI 85) but weak price position (rank 6/8). Opportunity to capture more ADR.", source reputation.

- **REPUTATION_PRICE_MISMATCH (warning):** can_premium True y price_perception con "caro" → type REPUTATION_PRICE_MISMATCH, severity warning, message "Reputation supports premium but guests perceive price as high. Balance ADR and perception.", source reputation.

---

## 6. LÍMITES DEL SISTEMA

- Las alertas dependen de la estructura actual de agent_outputs; si un agente cambia formato (p. ej. demand_index o rate_parity), hay que actualizar detect_alerts.
- No hay persistencia ni historial de alertas; cada corrida genera la lista desde cero.
- Los umbrales (ALERT_CONFIG) son fijos; no hay calibración por mercado ni por tipo de hotel.
- El report agent sigue siendo LLM; puede no mencionar o priorizar alertas si no sigue el prompt.
- No hay escalado ni notificaciones automáticas (email, dashboard); las alertas solo están en el briefing y en el informe generado.
- No se ha tocado job_schema, job_state, job_runtime, job_watchdog, job_recovery, job_observability, admin_panel ni analysis_runner.
