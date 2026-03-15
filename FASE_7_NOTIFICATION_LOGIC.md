# Fase 7 — Notification / Delivery Logic

---

## 1. PROBLEMA QUE RESUELVE NOTIFICATION LOGIC

Antes de la Fase 7, RevMax detectaba alertas, market signals y acciones recomendadas, pero no decidía de forma explícita **qué merece ser comunicado**, con qué prioridad y en qué formato. No existía una capa que filtrara y priorizara los hallazgos para comunicación ejecutiva.

La Notification Logic:

- Determina **por código** qué hallazgos son realmente comunicables y con qué nivel de prioridad (urgent | high | medium | low).
- Produce un resumen y un formato estándar por notificación: type, priority, title, summary, rationale, source_items, delivery_intent (immediate_attention | include_in_report | monitor_only).
- Combina alertas, market_signals, recommended_actions, derived_overall_status y strategy_label para evitar duplicados y agrupar cuando procede.
- No envía emails ni ejecuta nada; solo genera el bundle (notification_candidates, top_notifications, notification_summary, notification_priority_counts) para que el report y futuros canales lo consuman.

Así, RevMax separa claramente “qué notificar” y “con qué prioridad/formato” de la ejecución o el envío.

---

## 2. ARCHIVOS MODIFICADOS

- **notification_logic.py** (nuevo): módulo con `build_notification_bundle(briefing)`, `_build_notification_summary(notifications)`, `_build_priority_counts(notifications)`, constantes `NOTIFICATION_PRIORITIES`, `DELIVERY_INTENTS`, `MAX_TOP_NOTIFICATIONS`, `PRIORITY_ORDER` y helper `_notification(...)`.
- **orchestrator.py**: import de `build_notification_bundle`; después del bloque de recommended_actions en `run_full_analysis` y en `run_fast_demo`: llamada a `build_notification_bundle(briefing)` y asignación en el briefing de `notification_candidates`, `top_notifications`, `notification_summary`, `notification_priority_counts`.
- **agents/agent_07_report.py**: lectura de `top_notifications`, `notification_summary`, `notification_priority_counts`; bloque "NOTIFICACIONES PRIORIZADAS POR REVMAX" en el prompt con lista formateada; regla para que las notificaciones urgent/high influyan en el tono ejecutivo y no se inventen notificaciones fuera de las generadas por código.
- **tests/test_notification_logic.py** (nuevo): tests para parity critical + FIX_PARITY => urgent notification, weak demand + monitor => medium/low, underpriced + increase => high, low visibility + improve visibility => high/medium, defensive + critical => defensive notification, deduplicación y máximo 5 top_notifications, briefing vacío.

---

## 3. CAMBIOS IMPLEMENTADOS

- **Tipos de notificación:** CRITICAL_PARITY_NOTIFICATION, DEFENSIVE_POSTURE_NOTIFICATION, DEMAND_RISK_NOTIFICATION, PRICE_OPPORTUNITY_NOTIFICATION, UNDERVALUATION_OPPORTUNITY_NOTIFICATION, VISIBILITY_ISSUE_NOTIFICATION. Cada una con type, priority, title, summary, rationale, source_items (lista), delivery_intent.
- **Reglas de generación:** PARITY_VIOLATION + FIX_PARITY => CRITICAL_PARITY_NOTIFICATION urgent immediate_attention; DEFENSIVE + critical/high alerts => DEFENSIVE_POSTURE_NOTIFICATION urgent/high; DEMAND_COLLAPSE / WEAK_DEMAND + MONITOR_DEMAND o HOLD_PRICE => DEMAND_RISK_NOTIFICATION high/medium; PRICE_INCREASE + DEMAND_SUPPORTS o COMPETITOR_PRICE_PRESSURE => PRICE_OPPORTUNITY_NOTIFICATION high; UNDERPRICED + PRICE_INCREASE o REVIEW_POSITIONING => UNDERVALUATION_OPPORTUNITY_NOTIFICATION high; LOW_VISIBILITY + IMPROVE_VISIBILITY => VISIBILITY_ISSUE_NOTIFICATION high/medium; PRICE_DECREASE + overpriced signals => DEMAND_RISK (si no hay ya uno por demanda débil).
- **Priorización:** critical alert + urgent action => urgent; high alert + high action => high; señales fuertes sin alert crítica => high o medium; monitorización => medium/low. Deduplicación por type (mayor prioridad gana); máximo 5 top_notifications.
- **Orchestrator:** Tras recommended_actions se llama `build_notification_bundle(briefing)` y se añaden al briefing los cuatro campos del bundle.
- **Report:** Bloque "NOTIFICACIONES PRIORIZADAS POR REVMAX" con summary, priority_counts y lista; regla para que urgent/high influyan en el tono y no se inventen notificaciones.

---

## 4. CÓDIGO COMPLETO

### notification_logic.py

El archivo completo está en el workspace: cabecera del módulo, NOTIFICATION_PRIORITIES, DELIVERY_INTENTS, MAX_TOP_NOTIFICATIONS, PRIORITY_ORDER, _notification(...), build_notification_bundle (con las siete familias de candidatos, deduplicación por tipo y ordenación), _build_notification_summary y _build_priority_counts.

### Cambios en orchestrator.py

**Import (junto a action_planner):**
```python
from notification_logic import build_notification_bundle
```

**Tras el bloque de recommended_priority_actions_seed en run_full_analysis:**
```python
    notification_bundle = build_notification_bundle(briefing)
    briefing["notification_candidates"] = notification_bundle["notification_candidates"]
    briefing["top_notifications"] = notification_bundle["top_notifications"]
    briefing["notification_summary"] = notification_bundle["notification_summary"]
    briefing["notification_priority_counts"] = notification_bundle["notification_priority_counts"]
```

**En run_fast_demo:** el mismo bloque tras recommended_priority_actions_seed y antes de full_analysis.

### Cambios en agents/agent_07_report.py

**Variables del briefing (después de high_priority_action_count):**
```python
    top_notifications = briefing.get("top_notifications", [])
    notification_summary = briefing.get("notification_summary", "")
    notification_priority_counts = briefing.get("notification_priority_counts", {})
```

**Bloque nuevo en el prompt (después de ACCIONES RECOMENDADAS POR REVMAX):**
```
NOTIFICACIONES PRIORIZADAS POR REVMAX (generadas por código; no inventar notificaciones fuera de esta lista; usar title, summary y rationale):
  notification_summary: ...
  notification_priority_counts: ...
  Lista de notificaciones (top_notifications; si hay urgent/high deben influir en el tono ejecutivo del informe):
  [PRIORITY] type (delivery_intent): title | summary: ... | rationale: ... | source_items: ...
```

**Regla nueva antes de "Genera el informe siguiendo EXACTAMENTE...":**
```
- NOTIFICACIONES: Si hay top_notifications con prioridad urgent o high, deben influir en el tono ejecutivo del report (énfasis en lo que requiere atención inmediata o inclusión clara en el informe). No inventes notificaciones fuera de las generadas por código. Usa title, summary y rationale de cada notificación; conecta con actions y alerts en el texto.
```

### tests/test_notification_logic.py

El archivo completo está en el workspace: 7 tests (parity critical + FIX_PARITY => urgent, weak demand + monitor => medium, underpriced + increase => high, low visibility + improve => high/medium, defensive + critical => defensive, deduplicación y máximo 5 top, briefing vacío sin crash).

---

## 5. EJEMPLOS REALES DE NOTIFICACIONES

- **CRITICAL_PARITY_NOTIFICATION:** alerts con PARITY_VIOLATION y recommended_actions con FIX_PARITY => type CRITICAL_PARITY_NOTIFICATION, priority urgent, title "Parity issue requires immediate attention", summary "Rate parity violation detected across channels.", rationale "Critical alert and action FIX_PARITY both point to immediate intervention.", source_items ["PARITY_VIOLATION", "FIX_PARITY"], delivery_intent immediate_attention.

- **DEFENSIVE_POSTURE_NOTIFICATION:** strategy_label DEFENSIVE y (alerta critical o derived_overall_status alert) => type DEFENSIVE_POSTURE_NOTIFICATION, priority urgent si critical sino high, title "Defensive posture with active alerts", summary "Strategy is DEFENSIVE and there are critical or high-severity alerts; avoid risky price moves.", rationale "Alerts and defensive strategy both indicate stabilising position before any aggressive action.", source_items ["strategy_DEFENSIVE", "alerts_critical_or_high"], delivery_intent immediate_attention o include_in_report.

- **DEMAND_RISK_NOTIFICATION:** DEMAND_COLLAPSE o WEAK_DEMAND_REQUIRES_CAUTION con MONITOR_DEMAND/HOLD_PRICE => type DEMAND_RISK_NOTIFICATION, priority high si DEMAND_COLLAPSE sino medium, title "Demand risk requires caution", summary "Demand is weak or collapsed; do not raise prices; monitor and hold recommended.", rationale "Alert or market signal and recommended actions align on caution.", source_items según alertas/acciones, delivery_intent include_in_report o monitor_only.

- **PRICE_OPPORTUNITY_NOTIFICATION:** PRICE_INCREASE en acciones y (DEMAND_SUPPORTS_INCREASE o COMPETITOR_PRICE_PRESSURE) en señales => type PRICE_OPPORTUNITY_NOTIFICATION, priority high, title "Price increase opportunity", summary "Consolidation and market signals support a price increase; demand or competition supports capture.", rationale "Recommended action PRICE_INCREASE aligned with strong market signals.", source_items ["PRICE_INCREASE", "DEMAND_SUPPORTS_INCREASE", ...], delivery_intent include_in_report.

- **UNDERVALUATION_OPPORTUNITY_NOTIFICATION:** UNDERPRICED_RELATIVE_TO_POSITION y (PRICE_INCREASE o REVIEW_POSITIONING) => type UNDERVALUATION_OPPORTUNITY_NOTIFICATION, priority high, title "Undervaluation opportunity", summary "Reputation and position support higher price than currently achieved; increase or review recommended.", rationale "Market signal UNDERPRICED_RELATIVE_TO_POSITION and actions align on capturing more ADR.", source_items ["UNDERPRICED_RELATIVE_TO_POSITION", "PRICE_INCREASE", ...], delivery_intent include_in_report.

- **VISIBILITY_ISSUE_NOTIFICATION:** LOW_VISIBILITY y IMPROVE_VISIBILITY => type VISIBILITY_ISSUE_NOTIFICATION, priority high, title "Visibility issue requires action", summary "Visibility score is below threshold; improve OTA presence recommended.", rationale "LOW_VISIBILITY alert and IMPROVE_VISIBILITY action both point to visibility as a priority.", source_items ["LOW_VISIBILITY", "IMPROVE_VISIBILITY"], delivery_intent include_in_report.

---

## 6. LÍMITES DEL SISTEMA

- La lógica depende del contenido actual del briefing (alerts, market_signals, recommended_actions, derived_overall_status, strategy_label); cambios en Alert Engine, Market Signals o Action Planner pueden requerir ajustes en build_notification_bundle.
- No hay envío automático, scheduler, emails ni transports; la capa solo produce el bundle para consumo del report y futuros canales.
- No hay persistencia histórica de notificaciones; cada ejecución genera el bundle desde cero.
- El report agent sigue siendo LLM; puede no reflejar bien el tono urgente/high si no sigue el prompt, pero la lista de notificaciones es fija por código.
- Máximo 5 top_notifications; deduplicación por type puede colapsar notificaciones de distinto origen en una sola.
- La taxonomía de tipos (CRITICAL_PARITY_NOTIFICATION, DEMAND_RISK_NOTIFICATION, etc.) es fija; ampliarla requiere modificar notification_logic.py y, si aplica, el report.
