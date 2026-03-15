# FASE 14 — Change Detection Engine

## 1. PROBLEMA QUE RESUELVE CHANGE DETECTION ENGINE

RevMax analiza cada corrida de forma puntual pero no exponía de forma explícita **qué ha cambiado** respecto a la corrida anterior ni **por qué importa** para un director o revenue manager.

El **Change Detection Engine** añade una capa que usa el snapshot previo (Intelligence Memory) para comparar de forma **semántica** (etiquetas, tipos, escenarios, top priority, estado global) y producir un resumen de cambios, severidad y highlights. No rehace la memoria; se apoya en la ya guardada y complementa con foco en cambios relevantes para la decisión.

---

## 2. ARCHIVOS MODIFICADOS

| Archivo | Acción |
|---------|--------|
| `change_detection_engine.py` | **Creado** — build_change_detection(briefing, previous_snapshot) |
| `intelligence_memory.py` | **Modificado** — campos extra en snapshot, previous_snapshot en bundle, update_latest_snapshot |
| `orchestrator.py` | **Modificado** — integración tras Scenario/Exec, update_latest_snapshot |
| `agents/agent_07_report.py` | **Modificado** — bloque CAMBIOS DETECTADOS DESDE LA CORRIDA ANTERIOR |
| `tests/test_change_detection_engine.py` | **Creado** — tests unitarios |
| `FASE_14_CHANGE_DETECTION.md` | **Creado** — esta documentación |

No tocados: job_schema, job_state, job_runtime, job_watchdog, job_recovery, job_observability, admin_panel, analysis_runner. No rotos: consolidate, Strategy, Alert, Market Signals, Decision Engine, Notification Logic, Intelligence Memory, Opportunity Engine, Impact Engine, Value Prioritization, Scenario Engine, Executive Output, Report Agent, tests existentes.

---

## 3. CAMBIOS IMPLEMENTADOS

- **change_detection_engine.py**
  - build_change_detection(briefing, previous_snapshot) usa el snapshot previo (o None). Reutiliza strategy_changed, overall_status_changed, action_shift, new_alerts, resolved_alerts del briefing (ya rellenados por Intelligence Memory). Calcula: consolidated_action_changed, top_priority_changed, top_value_opportunity_changed, recommended_scenario_changed, new_critical_alerts, resolved_critical_alerts, new_high_alerts, resolved_high_alerts (con critical_alert_types/high_alert_types del snapshot), new_top_notifications, resolved_top_notifications, opportunity_shift, scenario_shift. Asigna change_severity (low | medium | high): high si hay new_critical_alerts; medium si strategy/status/action/scenario/top_priority cambian o new_high/resolved_critical. change_summary y change_highlights a partir de los cambios detectados.

- **intelligence_memory.py**
  - _snapshot_from_briefing: añadidos critical_alert_types, high_alert_types, opportunity_types, top_priority_item_type, top_value_opportunity_type, recommended_scenario para que el snapshot sea comparable en la siguiente corrida.
  - build_memory_bundle: devuelve "previous_snapshot" (el dict cargado o None).
  - _latest_snapshot_path(hotel_name, base_path): devuelve la ruta del snapshot más reciente.
  - update_latest_snapshot(briefing, hotel_name, base_path): reescribe el snapshot más reciente con _snapshot_from_briefing(briefing) para que incluya datos de Impact/Value/Scenario.

- **orchestrator.py**
  - Import build_change_detection y update_latest_snapshot. Tras Scenario y Executive Output: change_results = build_change_detection(briefing, memory_bundle.get("previous_snapshot")); briefing.update(change_results); update_latest_snapshot(briefing, hotel_name, _ORCH_BASE_DIR). Igual en run_fast_demo.

- **agents/agent_07_report.py**
  - Variables: change_summary, change_severity, change_highlights, strategy_changed, overall_status_changed, consolidated_action_changed, top_priority_changed, recommended_scenario_changed, new_critical_alerts, resolved_critical_alerts.
  - Bloque "CAMBIOS DETECTADOS DESDE LA CORRIDA ANTERIOR" con change_summary, change_severity, change_highlights y flags.
  - Regla CAMBIOS: usar solo esos datos; si no hay cambios relevantes decirlo; si change_severity high deben aparecer en resumen ejecutivo; si strategy/scenario/top_priority cambian explicarlo; no inventar cambios.

- **tests/test_change_detection_engine.py**
  - Sin corrida previa => sin cambios relevantes / change_summary; strategy_changed; new_critical_alert y severity high; resolved_critical_alert; top_priority_changed; recommended_scenario_changed; change_severity high con critical nueva; change_summary existe; change_highlights existe.

---

## 4. CÓDIGO COMPLETO

### change_detection_engine.py

Ver archivo en el repositorio: _curr_critical_alert_types, _curr_high_alert_types, _curr_top_notification_types, _curr_opportunity_types, _curr_action_types; build_change_detection(briefing, previous_snapshot) que rellena todos los campos listados y devuelve el dict de cambio.

### intelligence_memory.py (fragmentos)

- _snapshot_from_briefing: añadidos critical_alert_types, high_alert_types, opportunity_types, top_priority_item_type, top_value_opportunity_type, recommended_scenario.
- _latest_snapshot_path, load_previous_snapshot (usa _latest_snapshot_path), update_latest_snapshot.
- build_memory_bundle: return incluye "previous_snapshot": previous.

### orchestrator.py (fragmentos)

- Import: from intelligence_memory import build_memory_bundle, update_latest_snapshot; from change_detection_engine import build_change_detection.
- Tras exec_briefing: change_results = build_change_detection(briefing, memory_bundle.get("previous_snapshot")); briefing.update(change_results); update_latest_snapshot(briefing, hotel_name, _ORCH_BASE_DIR).

### agent_07_report.py (fragmentos)

- Lectura de change_* y flags; bloque "CAMBIOS DETECTADOS DESDE LA CORRIDA ANTERIOR"; regla CAMBIOS.

### tests/test_change_detection_engine.py

Nueve tests según apartado 3.

---

## 5. EJEMPLOS DE CAMBIOS DETECTADOS

- **Sin corrida previa:** change_summary = "No previous run to compare..."; change_severity = low.
- **Strategy BALANCED → DEFENSIVE:** strategy_changed True; change_highlights incluye "Strategy changed from BALANCED to DEFENSIVE."
- **Nueva PARITY_VIOLATION (critical):** new_critical_alerts = ["PARITY_VIOLATION"]; change_severity = high; highlight "New critical alert(s): PARITY_VIOLATION."
- **Paridad resuelta:** resolved_critical_alerts = ["PARITY_VIOLATION"]; highlight "Resolved critical alert(s): PARITY_VIOLATION."
- **Top priority FIX_PARITY → PRICE_INCREASE:** top_priority_changed True; highlight "Top priority item changed."
- **Escenario raise → hold:** recommended_scenario_changed y scenario_shift True; highlight "Recommended scenario changed from raise to hold."

---

## 6. LÍMITES DEL SISTEMA

- No hay timeline visual, dashboard nuevo, persistencia histórica adicional, ML, scheduler ni notificaciones automáticas.
- La comparación es con la **corrida anterior** únicamente; no con N corridas ni ventanas temporales.
- change_severity es heurístico (nueva critical => high; cambios de strategy/status/action/scenario => medium).
- El snapshot se actualiza con update_latest_snapshot al final de la corrida para que la siguiente tenga top_priority_item, recommended_scenario, etc.; la primera corrida tras el despliegue no tendrá esos cambios hasta la segunda corrida.
- No se modifica el Job Engine.
