# Fase 9 — Opportunity Engine

---

## 1. PROBLEMA QUE RESUELVE OPPORTUNITY ENGINE

Antes de la Fase 9, RevMax detectaba riesgos (alertas), señales de mercado, acciones recomendadas y notificaciones, pero no generaba de forma explícita **oportunidades concretas de captura de valor o mejora de posicionamiento**. Las oportunidades quedaban implícitas o vagas.

El Opportunity Engine:

- Detecta **por código** oportunidades explícitas, priorizadas y explicables, alineadas con estrategia, señales, acciones y notificaciones.
- Diferencia **oportunidad** (posibilidad de captura o mejora) de **alerta** (riesgo) y de **acción** (qué hacer).
- Produce una taxonomía clara: PRICE_CAPTURE_OPPORTUNITY, UNDERVALUATION_OPPORTUNITY, DEFENSIVE_STABILIZATION_OPPORTUNITY, VISIBILITY_RECOVERY_OPPORTUNITY, DEMAND_RECOVERY_OPPORTUNITY.
- Cada oportunidad incluye opportunity_level (low | medium | high), title, summary, rationale, source_items, potential_value y recommended_posture.
- Deduplicación por tipo y máximo 5 oportunidades.

Así, RevMax puede comunicar no solo qué hacer y qué riesgos hay, sino también qué oportunidades de revenue o posicionamiento existen.

---

## 2. ARCHIVOS MODIFICADOS

- **opportunity_engine.py** (nuevo): módulo con `_opportunity(...)`, `build_opportunities(briefing)`, `build_opportunity_summary(opportunities)`, `count_high_opportunities(opportunities)`, `get_opportunity_types(opportunities)`; constantes `OPPORTUNITY_LEVELS`, `MAX_OPPORTUNITIES`, `LEVEL_ORDER`.
- **orchestrator.py**: import de `build_opportunities`, `build_opportunity_summary`, `count_high_opportunities`, `get_opportunity_types`; después del bloque de intelligence_memory en `run_full_analysis` y en `run_fast_demo`: llamada a `build_opportunities(briefing)` y asignación en el briefing de `opportunities`, `opportunity_summary`, `high_opportunity_count`, `opportunity_types`. El campo `opportunities` del briefing pasa a ser la lista generada por el engine (sustituye la lista de strings de consolidate para el report).
- **agents/agent_07_report.py**: lectura de `opportunities`, `opportunity_summary`, `high_opportunity_count`, `opportunity_types`; bloque "OPORTUNIDADES IDENTIFICADAS POR REVMAX" en el prompt con lista formateada por oportunidad (level, type, title, summary, rationale, source_items, potential_value, recommended_posture); regla OPORTUNIDADES para que las high aparezcan en report_text, conectar con acciones y estrategia, no inventar y diferenciar de alerta/acción.
- **tests/test_opportunity_engine.py** (nuevo): tests para reputación+demanda+underpriced => PRICE_CAPTURE high, underpriced => UNDERVALUATION, defensive+critical => DEFENSIVE_STABILIZATION, low visibility+improve => VISIBILITY_RECOVERY, weak demand+monitor => DEMAND_RECOVERY, deduplicación y máximo 5, summary y counts, briefing vacío.

---

## 3. CAMBIOS IMPLEMENTADOS

- **Tipos de oportunidad:** PRICE_CAPTURE_OPPORTUNITY (reputación/posición/demanda permiten más ADR), UNDERVALUATION_OPPORTUNITY (hotel infravalorado vs posicionamiento), DEFENSIVE_STABILIZATION_OPPORTUNITY (proteger ingresos/posición evitando riesgos), VISIBILITY_RECOVERY_OPPORTUNITY (mejorar visibilidad para destrabar demanda o pricing power), DEMAND_RECOVERY_OPPORTUNITY (reaccionar mejor a debilidad de demanda con ajuste/protección).
- **Estructura por oportunidad:** type, opportunity_level, title, summary, rationale, source_items, potential_value (adr_capture | positioning | revenue_protection | visibility | demand_alignment), recommended_posture (raise | hold | lower | review | improve_visibility | monitor).
- **Reglas de generación:** consolidated raise + DEMAND_SUPPORTS y/o UNDERPRICED => PRICE_CAPTURE (high si varias señales o PREMIUM/AGGRESSIVE); UNDERPRICED sin PRICE_CAPTURE => UNDERVALUATION; DEFENSIVE + critical/high o PROTECT_RATE/HOLD_PRICE => DEFENSIVE_STABILIZATION; LOW_VISIBILITY + IMPROVE_VISIBILITY => VISIBILITY_RECOVERY high; WEAK_DEMAND o DEMAND_COLLAPSE + MONITOR/PRICE_DECREASE/HOLD => DEMAND_RECOVERY; hold + MARKET_COMPRESSION o WEAK_DEMAND sin DEFENSIVE => DEFENSIVE_STABILIZATION medium.
- **Priorización y tope:** high > medium > low; deduplicación por type; máximo 5 oportunidades.
- **Orchestrator:** integración en ambos flujos tras intelligence_memory.
- **Report:** bloque OPORTUNIDADES IDENTIFICADAS y regla para high en report_text, conexión con acciones/estrategia y no inventar.

---

## 4. CÓDIGO COMPLETO

### opportunity_engine.py

El archivo completo está en el workspace: cabecera, OPPORTUNITY_LEVELS, MAX_OPPORTUNITIES, LEVEL_ORDER, _opportunity(...), build_opportunities (con seis familias de candidatos, deduplicación por tipo y ordenación), build_opportunity_summary, count_high_opportunities, get_opportunity_types.

### Cambios en orchestrator.py

**Import:**
```python
from opportunity_engine import (
    build_opportunities,
    build_opportunity_summary,
    count_high_opportunities,
    get_opportunity_types,
)
```

**Tras el bloque de action_shift en run_full_analysis:**
```python
    opportunities = build_opportunities(briefing)
    briefing["opportunities"] = opportunities
    briefing["opportunity_summary"] = build_opportunity_summary(opportunities)
    briefing["high_opportunity_count"] = count_high_opportunities(opportunities)
    briefing["opportunity_types"] = get_opportunity_types(opportunities)
```

**En run_fast_demo:** el mismo bloque tras action_shift y antes de full_analysis.

### Cambios en agents/agent_07_report.py

**Variables del briefing:** opportunities, opportunity_summary, high_opportunity_count, opportunity_types (leyendo del briefing; opportunities pasa a ser la lista de dicts del engine).

**Bloque en el prompt:** "OPORTUNIDADES IDENTIFICADAS POR REVMAX" con opportunity_summary, high_opportunity_count, opportunity_types y lista formateada por oportunidad (level, type, title, summary, rationale, source_items, potential_value, recommended_posture).

**Regla:** "OPORTUNIDADES: Si hay oportunidades de nivel high, deben aparecer en report_text. Conecta oportunidades con acciones y estrategia. No inventes oportunidades fuera de las generadas por código. Diferencia claramente oportunidad (posibilidad de captura o mejora) de alerta (riesgo) o de acción (qué hacer)."

### tests/test_opportunity_engine.py

El archivo completo está en el workspace: 8 tests (reputation+demand+underpriced => PRICE_CAPTURE high, underpriced => UNDERVALUATION, defensive+critical => DEFENSIVE_STABILIZATION, low visibility+improve => VISIBILITY_RECOVERY, weak demand+monitor => DEMAND_RECOVERY, deduplicación y máximo 5, summary y counts, briefing vacío).

---

## 5. EJEMPLOS REALES DE OPORTUNIDADES

- **PRICE_CAPTURE_OPPORTUNITY (high):** strategy PREMIUM, consolidated raise, market_signals DEMAND_SUPPORTS_INCREASE y UNDERPRICED_RELATIVE_TO_POSITION => type PRICE_CAPTURE_OPPORTUNITY, opportunity_level high, title "Opportunity to capture additional ADR", summary "Current positioning suggests room to increase price without materially weakening competitiveness.", rationale "Demand, reputation and/or current ranking suggest the hotel may be leaving value on the table.", source_items ["DEMAND_SUPPORTS_INCREASE", "UNDERPRICED_RELATIVE_TO_POSITION", "strategy_PREMIUM"], potential_value adr_capture, recommended_posture raise.

- **UNDERVALUATION_OPPORTUNITY:** signal UNDERPRICED_RELATIVE_TO_POSITION, action REVIEW_POSITIONING => type UNDERVALUATION_OPPORTUNITY, opportunity_level medium o high, title "Undervaluation vs positioning and reputation", potential_value positioning, recommended_posture review o raise.

- **DEFENSIVE_STABILIZATION_OPPORTUNITY:** strategy DEFENSIVE, alert critical, action PROTECT_RATE => type DEFENSIVE_STABILIZATION_OPPORTUNITY, opportunity_level high, title "Opportunity to stabilize and protect revenue", summary "Defensive posture and active alerts create an opportunity to protect revenue and position by avoiding risky price moves.", potential_value revenue_protection, recommended_posture hold.

- **VISIBILITY_RECOVERY_OPPORTUNITY:** alert LOW_VISIBILITY, action IMPROVE_VISIBILITY => type VISIBILITY_RECOVERY_OPPORTUNITY, opportunity_level high, title "Opportunity to recover visibility and unlock demand", potential_value visibility, recommended_posture improve_visibility.

- **DEMAND_RECOVERY_OPPORTUNITY:** signal WEAK_DEMAND_REQUIRES_CAUTION, actions MONITOR_DEMAND y HOLD_PRICE => type DEMAND_RECOVERY_OPPORTUNITY, opportunity_level medium, title "Opportunity to align with weak demand and protect occupancy", potential_value demand_alignment, recommended_posture hold o monitor.

---

## 6. LÍMITES DEL SISTEMA

- Las oportunidades dependen del contenido actual del briefing (strategy_label, consolidated_price_action, alerts, market_signals, recommended_actions, top_notifications); cambios en consolidate, Strategy Engine, Alert Engine, Market Signals o Action Planner pueden requerir ajustes en build_opportunities.
- No hay forecast cuantitativo ni estimación monetaria compleja; potential_value es una etiqueta (adr_capture, positioning, etc.), no un importe.
- No hay persistencia específica de oportunidades ni dashboard nuevo; el engine solo produce la lista por corrida.
- El report agent sigue siendo LLM; puede no reflejar bien las oportunidades high o no diferenciarlas de alertas/acciones si no sigue el prompt.
- Máximo 5 oportunidades; la deduplicación por tipo puede colapsar variantes de la misma familia en una sola.
- La taxonomía de tipos y potential_value es fija; ampliarla requiere modificar opportunity_engine.py y, si aplica, el report.
