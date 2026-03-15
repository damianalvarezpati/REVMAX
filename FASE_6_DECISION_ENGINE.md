# Fase 6 — Decision Engine / Action Planner

---

## 1. PROBLEMA QUE RESUELVE EL DECISION ENGINE

Antes de la Fase 6, RevMax analizaba, detectaba estrategia, alertas y señales de mercado, pero no producía una lista explícita de **acciones concretas, priorizadas y ejecutables**. El report agent podía inventar o reformular acciones sin una base determinista.

El Decision Engine (Action Planner):

- Genera **por código** una lista de acciones operativas y estratégicas coherentes con la consolidación, la estrategia, las alertas y las market signals.
- Asigna a cada acción: tipo, prioridad (low | medium | high | urgent), horizonte (immediate | this_week | monitor), título, rationale, source_signals y expected_effect.
- Deduplica por tipo (se mantiene la de mayor prioridad) y limita a un máximo de 5 acciones.
- El report agent **solo redacta y contextualiza** esas acciones; no las inventa.

Así, las acciones recomendadas existen de forma determinista y trazable antes de que el LLM las explique en el informe.

---

## 2. ARCHIVOS MODIFICADOS

- **action_planner.py** (nuevo): módulo con `build_recommended_actions(agent_outputs, conflicts, consolidation_result)`, `build_recommended_action_summary(actions)`, `count_actions_by_priority(actions, priority)`, constantes `ACTION_PRIORITIES`, `ACTION_HORIZONS`, `MAX_RECOMMENDED_ACTIONS`, `PRIORITY_ORDER`, `HORIZON_ORDER` y helper `_action(...)`.
- **orchestrator.py**: import de `build_recommended_actions`, `build_recommended_action_summary`, `count_actions_by_priority`; después del bloque de market_signals en `run_full_analysis` y en `run_fast_demo`: llamada a `build_recommended_actions`, asignación en el briefing de `recommended_actions`, `recommended_action_summary`, `urgent_action_count`, `high_priority_action_count` y `recommended_priority_actions_seed` (derivado de recommended_actions para el report).
- **agents/agent_07_report.py**: lectura de `recommended_actions`, `recommended_action_summary`, `urgent_action_count`, `high_priority_action_count`; bloque "ACCIONES RECOMENDADAS POR REVMAX" en el prompt con lista formateada; regla que exige que las priority_actions se basen exclusivamente en esa lista, sin inventar, con urgent primero y máximo 3 en el JSON.
- **tests/test_action_planner.py** (nuevo): tests para parity => FIX_PARITY urgent, underpriced + demand => PRICE_INCREASE high, weak demand + overpriced => PRICE_DECREASE/HOLD_PRICE, low visibility => IMPROVE_VISIBILITY, defensive + critical => coherente, deduplicación y máximo 5, summary/counts y briefing vacío.

---

## 3. CAMBIOS IMPLEMENTADOS

- **Tipos de acción:** PRICE_INCREASE, PRICE_DECREASE, HOLD_PRICE, FIX_PARITY, IMPROVE_VISIBILITY, PROTECT_RATE, MONITOR_DEMAND, REVIEW_POSITIONING. Cada acción tiene type, priority, horizon, title, rationale, source_signals (lista), expected_effect.
- **Reglas de generación:** PARITY_VIOLATION => FIX_PARITY urgent immediate; LOW_VISIBILITY => IMPROVE_VISIBILITY high; DEFENSIVE + critical/alert => PROTECT_RATE; DEMAND_COLLAPSE / WEAK_DEMAND => MONITOR_DEMAND; OVERPRICED / PRICE_TOO_HIGH => PRICE_DECREASE; consolidated raise => PRICE_INCREASE (con source_signals de demanda/reputación); consolidated lower => PRICE_DECREASE; consolidated hold => HOLD_PRICE; UNDERPRICED sin raise => REVIEW_POSITIONING.
- **Priorización:** parity/alert critical => urgent; señales fuertes de mercado => high; monitorización => medium/low. Orden final: por prioridad descendente, luego por horizonte (immediate > this_week > monitor). Deduplicación por type manteniendo la de mayor prioridad; máximo 5 acciones.
- **Orchestrator:** Tras market_signals se llama `build_recommended_actions(outputs, conflicts, briefing)` y se añaden al briefing los cinco campos indicados más la semilla para el report.
- **Report:** Bloque "ACCIONES RECOMENDADAS POR REVMAX" con summary, counts y lista; regla obligatoria de basar priority_actions solo en recommended_actions, no inventar, urgent primero, máximo 3 en el informe.

---

## 4. CÓDIGO COMPLETO

### action_planner.py

El archivo completo está en el workspace: cabecera del módulo, ACTION_PRIORITIES, ACTION_HORIZONS, MAX_RECOMMENDED_ACTIONS, PRIORITY_ORDER, HORIZON_ORDER, _action(...), build_recommended_actions (con las nueve familias de candidatos, deduplicación por tipo y ordenación), build_recommended_action_summary y count_actions_by_priority.

### Cambios en orchestrator.py

**Import (junto a market_signals):**
```python
from action_planner import (
    build_recommended_actions,
    build_recommended_action_summary,
    count_actions_by_priority,
)
```

**Tras el bloque de market_signals en run_full_analysis:**
```python
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
```

**En run_fast_demo:** el mismo bloque tras el cálculo de market_signals y antes de `full_analysis = {...}`.

### Cambios en agents/agent_07_report.py

**Variables del briefing (después de market_caution_signal_count):**
```python
    recommended_actions = briefing.get("recommended_actions", [])
    recommended_action_summary = briefing.get("recommended_action_summary", "")
    urgent_action_count = briefing.get("urgent_action_count", 0)
    high_priority_action_count = briefing.get("high_priority_action_count", 0)
```

**Bloque nuevo en el prompt (después de SEÑALES DE MERCADO):**
```
ACCIONES RECOMENDADAS POR REVMAX (generadas por código; las priority_actions deben basarse SOLO en esta lista; no inventar ninguna acción fuera de ella):
  recommended_action_summary: ...
  urgent_action_count: ...
  high_priority_action_count: ...
  Lista de acciones (orden = prioridad; usar las 3 primeras para priority_actions o todas si son menos de 3):
  [PRIORITY] type (horizon): title | rationale: ... | source_signals: ... | expected_effect: ...
```

**Regla modificada (sustituye la de recommended_priority_actions_seed):**
```
- ACCIONES RECOMENDADAS: Las priority_actions deben BASARSE EXCLUSIVAMENTE en la lista "ACCIONES RECOMENDADAS POR REVMAX" anterior (recommended_actions). No inventes ninguna acción que no esté en esa lista. Orden: primero las urgent, luego high, luego el resto. Mantén priority, horizon y rationale de cada acción; conéctalas con strategy, alerts y market_signals en el texto. Máximo 3 priority_actions en el JSON (usa las 3 primeras de la lista o todas si son menos).
```

### tests/test_action_planner.py

El archivo completo está en el workspace: 8 tests (parity => FIX_PARITY urgent, underpriced + demand => PRICE_INCREASE high, weak demand + overpriced => PRICE_DECREASE/HOLD_PRICE, low visibility => IMPROVE_VISIBILITY, defensive + critical => coherente, deduplicación y máximo 5, summary y counts, briefing vacío sin crash).

---

## 5. EJEMPLOS REALES DE ACCIONES

- **FIX_PARITY (urgent, immediate):** alert type PARITY_VIOLATION → type FIX_PARITY, priority urgent, horizon immediate, title "Resolve rate parity across channels", rationale "Rate parity violation detected; hotel appears cheaper on OTA than direct. Must be fixed before any price change.", source_signals ["PARITY_VIOLATION"], expected_effect "Restore channel consistency and avoid contract/commission issues."

- **PRICE_INCREASE (high, this_week):** consolidated_action raise, market_signals DEMAND_SUPPORTS_INCREASE y UNDERPRICED_RELATIVE_TO_POSITION → type PRICE_INCREASE, priority high, horizon this_week, title "Increase price positioning", rationale "Consolidation recommends raise; demand and/or reputation support capturing more ADR.", source_signals ["DEMAND_SUPPORTS_INCREASE", "UNDERPRICED_RELATIVE_TO_POSITION"], expected_effect "Improve ADR capture without weakening competitive position."

- **PRICE_DECREASE (high, this_week):** signal OVERPRICED_FOR_CURRENT_DEMAND o alert PRICE_TOO_HIGH_FOR_DEMAND → type PRICE_DECREASE, priority high, horizon this_week, title "Reduce price to align with current demand", rationale "Pricing or signals indicate posture may be too high for current demand; consolidation favours hold or lower.", source_signals según señal/alerta, expected_effect "Improve occupancy and alignment with market."

- **HOLD_PRICE (medium/high, this_week):** consolidated_action hold, opcional WEAK_DEMAND_REQUIRES_CAUTION o MARKET_COMPRESSION o strategy DEFENSIVE → type HOLD_PRICE, priority high si hay alertas critical/high sino medium, horizon this_week, title "Hold current price", rationale "Consolidation recommends hold; signals support maintaining current posture.", source_signals ["consolidated_hold", ...], expected_effect "Preserve position until signals clarify."

- **IMPROVE_VISIBILITY (high, this_week):** alert LOW_VISIBILITY → type IMPROVE_VISIBILITY, priority high, horizon this_week, title "Improve OTA visibility and presence", rationale "Visibility score is below threshold; limits ability to capture demand.", source_signals ["LOW_VISIBILITY"], expected_effect "Better visibility supports both occupancy and pricing power."

- **PROTECT_RATE (urgent/high, immediate/this_week):** strategy_label DEFENSIVE y (alerta critical o derived_overall_status alert) → type PROTECT_RATE, priority urgent si critical sino high, horizon immediate si critical sino this_week, title "Protect current rate position", rationale "Strategy is DEFENSIVE and there are critical or high-severity alerts; avoid risky moves.", source_signals ["strategy_DEFENSIVE", "alerts_critical_or_high"], expected_effect "Stabilise position until alerts are resolved."

---

## 6. LÍMITES DEL SISTEMA

- Las acciones dependen de la estructura actual del briefing (consolidated_price_action, strategy_label, derived_overall_status, alerts, market_signals); cambios en consolidate(), Strategy Engine, Alert Engine o Market Signals pueden requerir ajustes en build_recommended_actions.
- No hay ejecución automática de acciones ni integración con PMS o Channel Manager; el Decision Engine solo produce la lista recomendada.
- No hay persistencia ni histórico de acciones; cada ejecución genera la lista desde cero.
- El report agent sigue siendo LLM; puede no redactar bien las acciones si no sigue el prompt, pero las acciones en sí son fijas por código.
- Máximo 5 acciones y deduplicación por tipo; si hay más de 5 tipos de candidatos, se pierden las de menor prioridad.
- La taxonomía de tipos (PRICE_INCREASE, PRICE_DECREASE, etc.) es fija; ampliarla requiere modificar action_planner.py y, si aplica, el report.
