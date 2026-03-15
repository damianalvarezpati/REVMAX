# Subfase 2B — Entrega: Consolidación y priorización analítica

---

## DEBILIDADES CORREGIDAS

1. **Pesos hardcodeados** en `consolidate()`: eliminados; centralizados en `CONSOLIDATION_WEIGHTS`.
2. **`consolidate()` monolítico**: dividido en helpers por responsabilidad (señales base, reputation, distribution, conflictos, dedup, rationale, derived status, seed).
3. **Priorización dejada al LLM**: añadidos `derived_overall_status` y `recommended_priority_actions_seed` deterministas; el report debe respetarlos.
4. **Falta de trazabilidad en el briefing**: añadidos `decision_drivers`, `decision_penalties`, `severity_summary`, `action_constraints` y uso explícito de `derived_overall_status` en el prompt del report.
5. **Sin tests de consolidación**: añadido `tests/test_consolidation.py` con 7 casos (raise+demand low→hold, paridad→hold+immediate, reputation+demand conflicto, dedup oportunidades, derived_overall_status con/sin critical_issues, pesos definidos).

---

## ARCHIVOS MODIFICADOS

- `orchestrator.py` — Refactor completo de consolidación y nuevos campos en briefing.
- `agents/agent_07_report.py` — Uso de `derived_overall_status`, `recommended_priority_actions_seed`, `decision_drivers`, `decision_penalties`, `severity_summary`, `action_constraints` en el prompt y reglas obligatorias.
- `tests/test_consolidation.py` — Nuevo archivo con tests unitarios de consolidación.

No se ha creado helper externo: toda la lógica de consolidación vive en `orchestrator.py` como funciones privadas (`_apply_*`, `_build_*`, `_derive_*`, etc.).

---

## CAMBIOS IMPLEMENTADOS

### Pesos centralizados

- Diccionario `CONSOLIDATION_WEIGHTS` al inicio de `orchestrator.py` con claves documentadas: `reputation_premium_raise_factor`, `reputation_overprice_lower_factor`, `parity_hold_boost`, `parity_raise_lower_multiplier`, `visibility_low_*`, `high_conflict_*`, `gri_min_for_premium`, `opportunity_max_count`, `opportunity_normalize_len`. Toda la lógica usa `CONSOLIDATION_WEIGHTS.get("key", default)`.

### División de `consolidate()`

- `consolidate()` queda como orquestador: obtiene pesos, aplica señales en cadena, obtiene acción final, construye listas y devuelve el briefing.
- Helpers:
  - `_get_confidence_weights`, `_apply_base_signals`, `_apply_reputation_signals`, `_apply_distribution_signals`, `_apply_conflict_penalties`, `_final_action_from_signals` — flujo de señales.
  - `_dedupe_opportunities`, `_build_alerts`, `_build_critical_issues`, `_build_signal_sources`, `_build_consolidation_rationale` — contenido del briefing.
  - `_derive_overall_status`, `_build_severity_summary`, `_build_decision_drivers`, `_build_decision_penalties`, `_build_action_constraints`, `_build_recommended_priority_actions_seed` — priorización y trazabilidad.

### Priorización más determinista

- `_derive_overall_status(critical_issues, parity_violation, has_high_conflict, demand_signal)`: devuelve `alert` si paridad o (conflicto high y demanda low/very_low), `needs_attention` si hay critical/issues pero no alert, `strong` si demanda high/very_high sin problemas, `stable` en resto.
- `_build_recommended_priority_actions_seed`: lista de hasta 3 ítems con `urgency`, `reason_source`, `action_hint`; paridad primero (immediate), luego conflicto si hay, luego acción consolidada (this_week). El report debe basar sus `priority_actions` en esta semilla.

### Trazabilidad

- Briefing incluye: `derived_overall_status`, `severity_summary` (high/medium conflicts y alerts, `has_critical`), `decision_drivers`, `decision_penalties`, `action_constraints`, `recommended_priority_actions_seed`.
- En `agent_07_report.py` el prompt incluye una sección "ESTADO Y PRIORIDAD DERIVADOS POR CÓDIGO" y reglas que obligan a usar `derived_overall_status` como `overall_status` y a basar `priority_actions` en la semilla sin contradecir urgencia ni orden.

### Tests

- `test_raise_plus_demand_low_results_in_hold`: pricing raise + demand low → consolidated_action hold, conflicto pricing_vs_demand, derived_overall_status alert/needs_attention.
- `test_parity_violation_hold_and_immediate_urgency`: parity violation → hold, derived_overall_status alert, primera acción en seed con urgency immediate y hint de paridad, action_constraints no vacío.
- `test_reputation_premium_demand_low_conflict`: reputation premium + demand low → conflicto reputation_vs_demand y severity_summary presente.
- `test_opportunity_deduplication`: misma descripción en pricing y demand → una sola oportunidad en el briefing.
- `test_derived_overall_status_with_critical_issues` y `test_derived_overall_status_stable_when_no_issues`: con/sin critical issues y paridad.
- `test_consolidation_weights_defined`: comprueba que existan las claves clave en CONSOLIDATION_WEIGHTS.

---

## CÓDIGO COMPLETO

Los tres archivos tocados están en el workspace con el código completo. Referencia rápida:

- **orchestrator.py**: CONSOLIDATION_WEIGHTS (líneas 30-43), detect_conflicts, _normalize_opportunity_text, _get_confidence_weights, _apply_base_signals, _apply_reputation_signals, _apply_distribution_signals, _apply_conflict_penalties, _final_action_from_signals, _dedupe_opportunities, _build_alerts, _build_critical_issues, _build_signal_sources, _build_consolidation_rationale, _derive_overall_status, _build_severity_summary, _build_decision_drivers, _build_decision_penalties, _build_action_constraints, _build_recommended_priority_actions_seed, consolidate (orquestador), _save, run_full_analysis, run_fast_demo, __main__.
- **agents/agent_07_report.py**: Variables del briefing (derived_overall_status, recommended_priority_actions_seed, decision_drivers, decision_penalties, severity_summary, action_constraints), bloque "ESTADO Y PRIORIDAD DERIVADOS POR CÓDIGO" en el prompt, REGLAS OBLIGATORIAS con overall_status y semilla de priority_actions.
- **tests/test_consolidation.py**: _base_outputs, 7 tests (raise+demand low, paridad, reputation+demand, dedup, derived status con/sin issues, weights).

Para ver el código completo literal, abrir en el IDE: `orchestrator.py`, `agents/agent_07_report.py`, `tests/test_consolidation.py`.

---

## ANTES VS DESPUÉS

### Ejemplo 1: Conflicto pricing raise + demand low

**Input simplificado**

- pricing.recommendation.action = "raise"
- demand.demand_index.signal = "low"
- demand.price_implication = "hold"
- Resto: parity ok, visibility 0.8, GRI 70.

**Antes**

- consolidate() sumaba señales con pesos inline; los conflictos high penalizaban raise y reforzaban hold. Decisión: hold, pero no había un `derived_overall_status` ni semilla de acciones; el report podía elegir overall_status "stable" o "strong" por su cuenta.

**Ahora**

- Decisión: `consolidated_price_action` = "hold".
- `derived_overall_status` = "alert" (has_high_conflict y demand_signal low).
- `recommended_priority_actions_seed`: primero ítem de conflicto/consolidación (this_week), con action_hint "Acción de precio consolidada: HOLD."
- `decision_drivers`: "Pricing recomienda raise...", "Demand implica hold...".
- `decision_penalties`: "Mantener precio. Esperar mejora de demanda antes de subir."
- `rationale` incluye "Conflictos de alta severidad aplicados → prioridad a hold."

---

### Ejemplo 2: Parity violation

**Input simplificado**

- pricing.recommendation.action = "raise"
- distribution.rate_parity.status = "violation"
- demand signal medium, resto normal.

**Antes**

- Paridad añadía conflicto high y en consolidate() se aplicaba parity_hold_boost y parity_raise_lower_multiplier; resultado hold. No había una primera acción "immediate" explícita ni restricciones en el briefing.

**Ahora**

- Decisión: `consolidated_price_action` = "hold".
- `derived_overall_status` = "alert" (parity_violation).
- `recommended_priority_actions_seed`: primer ítem urgency "immediate", reason_source "distribution", action_hint "Resolver violación de paridad de tarifas entre canales."
- `action_constraints`: "Resolver paridad antes de cualquier cambio de precio."
- `decision_penalties`: "Paridad violada: prioridad a hold hasta resolver."
- El report debe usar overall_status "alert" y la primera priority_action basada en esa semilla (paridad primero).

---

## LÍMITES QUE SIGUEN EXISTIENDO

- **Strategy engine / alert engine**: no implementados; la priorización sigue siendo reglas fijas en código (paridad, conflictos high, demanda).
- **Ajuste fino de pesos**: los valores en CONSOLIDATION_WEIGHTS son fijos; no hay calibración por hotel ni A/B.
- **Report agent**: sigue siendo LLM; puede seguir matizando o desviándose de la semilla si el prompt no se cumple al 100%; no hay capa de validación post-LLM que fuerce overall_status = derived_overall_status.
- **Conflictos**: la lista de tipos de conflicto y severidades está fija en `detect_conflicts`; no hay extensión por configuración.
- **Oportunidades**: la deduplicación es por texto normalizado (80 chars); puede colisionar en textos muy similares o perder matices.
- **Dashboard / APIs**: sin cambios; el briefing enriquecido solo lo consume el report agent y quien lea `full_analysis["briefing"]`.
