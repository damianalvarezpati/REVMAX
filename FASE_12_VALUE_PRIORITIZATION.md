# FASE 12 — Value Prioritization Engine

## 1. PROBLEMA QUE RESUELVE VALUE PRIORITIZATION ENGINE

RevMax ya produce alerts, market_signals, recommended_actions, opportunities, notifications, impact_opportunities e impact_actions, pero el orden de qué atender primero dependía de prioridad de acción, orden heurístico y límites del Executive Output, sin reflejar de forma explícita el valor económico o estratégico.

El **Value Prioritization Engine** introduce una capa que calcula **value_score**, **urgency_score**, **priority_score** y **priority_rank** para oportunidades y acciones, de modo que RevMax pueda decir qué oportunidad tiene más valor, qué acción es más urgente y qué debe atender primero el director, sin depender del LLM.

---

## 2. ARCHIVOS MODIFICADOS

| Archivo | Acción |
|---------|--------|
| `value_prioritization_engine.py` | **Creado** — motor de priorización por valor y urgencia |
| `orchestrator.py` | **Modificado** — integración tras Impact Engine |
| `agents/agent_07_report.py` | **Modificado** — uso de value_opportunities, value_actions y top_priority_item en el informe |
| `tests/test_value_prioritization.py` | **Creado** — tests unitarios del engine |
| `FASE_12_VALUE_PRIORITIZATION.md` | **Creado** — esta documentación |

No tocados: job_schema, job_state, job_runtime, job_watchdog, job_recovery, job_observability, admin_panel, analysis_runner. No rotos: consolidate, Strategy, Alert, Market Signals, Decision Engine, Notification Logic, Intelligence Memory, Opportunity Engine, Impact Engine, Executive Output.

---

## 3. CAMBIOS IMPLEMENTADOS

- **value_prioritization_engine.py**
  - `_get_prioritization_context(briefing)`: extrae alert_types, has_critical_alerts, has_high_alerts, signal_types, strategy_label, derived_overall_status.
  - Value score (0–5): por tipo de oportunidad/acción y impact_confidence (high/medium/low). Ej.: PRICE_CAPTURE_OPPORTUNITY con señales underpriced/demand → base alta; FIX_PARITY → base alta.
  - Urgency score (0–5): por alertas (PARITY_VIOLATION, LOW_VISIBILITY, etc.) y tipo (FIX_PARITY → 4.0; IMPROVE_VISIBILITY con LOW_VISIBILITY → 3.0; DEFENSIVE_STABILIZATION con critical → 3.0).
  - priority_score = value_score + urgency_score; orden por priority_score DESC; priority_rank 1, 2, 3...
  - top_priority_item: elemento (opportunity o action) con mayor priority_score; incluye item_type.
  - build_value_prioritization(briefing) devuelve: value_opportunities, value_actions, value_summary, top_priority_item.

- **orchestrator.py**
  - Import de build_value_prioritization.
  - Tras Impact Engine: value_results = build_value_prioritization(briefing); briefing.update(value_results). En run_full_analysis y run_fast_demo.

- **agents/agent_07_report.py**
  - Lectura de value_opportunities, value_actions, value_summary, top_priority_item.
  - Nuevo bloque en el prompt: "PRIORIZACIÓN POR VALOR Y URGENCIA" con value_summary, top_priority_item, listas value_opportunities y value_actions (hasta 5 ítems cada una) con priority_rank, value_score, urgency_score, priority_score e impact_estimate/action_impact_estimate.
  - Regla PRIORIDAD: usar solo value_opportunities y value_actions; no inventar scores; mostrar máximo 3 prioridades. Ejemplo: "Top priority opportunity: Capture additional ADR. Priority score: 8.2. Estimated impact: ADR upside +5–9%."

- **tests/test_value_prioritization.py**
  - value_opportunities existe; value_actions existe; priority_score = value_score + urgency_score; priority_rank correcto (orden DESC); top_priority_item existe y es el de mayor priority_score; no crash con briefing vacío.

---

## 4. CÓDIGO COMPLETO

### value_prioritization_engine.py

Ver archivo `value_prioritization_engine.py` en el repositorio. Contiene:

- VALUE_SCALE, URGENCY_SCALE (0–5).
- _get_prioritization_context(briefing).
- _confidence_bonus(conf).
- _opportunity_value_score(opp, ctx), _opportunity_urgency_score(opp, ctx).
- _action_value_score(action, ctx), _action_urgency_score(action, ctx).
- _enrich_opportunity(opp, ctx) → dict con type, title, impact_estimate, impact_confidence, value_score, urgency_score, priority_score, priority_rank.
- _enrich_action(action, ctx) → dict con type, title, action_impact_estimate, action_impact_confidence, value_score, urgency_score, priority_score, priority_rank.
- _assign_ranks(items) in-place.
- _pick_top_priority_item(value_opportunities, value_actions) → item con item_type "opportunity" | "action".
- _build_value_summary(...).
- build_value_prioritization(briefing) → {"value_opportunities", "value_actions", "value_summary", "top_priority_item"}.

### orchestrator.py (fragmentos)

- Import: `from value_prioritization_engine import build_value_prioritization`
- Tras `briefing.update(impact_results)`:
  - `value_results = build_value_prioritization(briefing)`
  - `briefing.update(value_results)`

### agents/agent_07_report.py (fragmentos)

- Variables: value_opportunities, value_actions, value_summary, top_priority_item.
- Bloque en el prompt: "PRIORIZACIÓN POR VALOR Y URGENCIA" con value_summary, top_priority_item, value_opportunities[:5], value_actions[:5] con campos priority_rank, value_score, urgency_score, priority_score, impact_estimate/action_impact_estimate.
- Regla: "PRIORIDAD: Usa SOLO value_opportunities y value_actions para Priority ranking, Value score y Urgency. No inventes scores. Muestra máximo 3 prioridades."

### tests/test_value_prioritization.py

Seis tests: test_value_opportunities_exists, test_value_actions_exists, test_priority_score_calculated, test_priority_rank_correct, test_top_priority_item_exists, test_no_crash_if_briefing_empty.

---

## 5. EJEMPLOS DE PRIORITIZACIÓN

| Tipo | Condiciones | value_score (aprox.) | urgency_score (aprox.) | priority_score |
|------|-------------|----------------------|------------------------|----------------|
| PRICE_CAPTURE_OPPORTUNITY | medium confidence, señales underpriced/demand | 3.1 | 1.5 | ~4.6 |
| FIX_PARITY | high confidence | 3.5 | 4.0 | ~7.5 |
| DEFENSIVE_STABILIZATION_OPPORTUNITY | critical alerts | 3.0 | 3.0 | ~6.0 |
| VISIBILITY_RECOVERY_OPPORTUNITY | LOW_VISIBILITY alert | 2.6 | 2.5 | ~5.1 |
| IMPROVE_VISIBILITY | LOW_VISIBILITY alert | 2.6 | 3.0 | ~5.6 |

Ejemplo en informe: "Top priority opportunity: Capture additional ADR. Priority score: 8.2. Estimated impact: ADR upside +5–9%."

---

## 6. LÍMITES DEL SISTEMA

- Scoring es heurístico (reglas fijas por tipo y contexto), no un modelo de valor económico real.
- Escalas 0–5 para value y urgency son fijas; no se calibran con datos históricos ni ML.
- top_priority_item es un solo ítem (oportunidad o acción); no hay ranking combinado explícito más allá de comparar priority_score.
- El report muestra hasta 5 ítems en las listas de priorización; la regla de "máximo 3 prioridades" es para el texto del informe, no para las listas en el prompt.
- Depende de que impact_opportunities e impact_actions estén ya en el briefing (Impact Engine debe ejecutarse antes).
