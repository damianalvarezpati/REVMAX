# Fase 8 — Persistence / Intelligence Memory Layer

---

## 1. PROBLEMA QUE RESUELVE INTELLIGENCE MEMORY

Antes de la Fase 8, cada análisis de RevMax era una corrida aislada: no se conservaba histórico estructurado ni se comparaba con ejecuciones anteriores. No había forma de detectar repetición, empeoramiento, mejora ni patrones entre corridas.

La Intelligence Memory:

- **Persiste** snapshots ligeros de inteligencia (strategy_label, derived_overall_status, alert_types, market_signal_types, recommended_action_types, top_notification_types, short_summary) por hotel en JSON bajo `data/intelligence_history/<hotel_slug>/`.
- **Recupera** el snapshot previo del mismo hotel para comparar.
- **Compara** corrida actual con la anterior y deriva repeated_alerts, new_alerts, resolved_alerts, repeated_notifications, strategy_changed, overall_status_changed, action_shift, attention_trend.
- **Produce** un memory_summary legible para el briefing y el report, sin base de datos compleja ni ML.

Así, RevMax puede decir si un problema persiste, si apareció uno nuevo, si se resolvieron alertas, si cambió la estrategia o el estado global y si la tendencia de atención empeora o mejora.

---

## 2. ARCHIVOS MODIFICADOS

- **intelligence_memory.py** (nuevo): módulo con `_hotel_slug`, `_history_dir`, `_build_short_summary`, `_snapshot_from_briefing`, `save_snapshot`, `load_previous_snapshot`, `compare_with_previous`, `_build_memory_summary`, `build_memory_bundle`; constantes `STATUS_ORDER`, `ATTENTION_TREND_VALUES`.
- **orchestrator.py**: import de `build_memory_bundle`; después del bloque de notification_logic en `run_full_analysis` y en `run_fast_demo`: llamada a `build_memory_bundle(briefing, hotel_name, _ORCH_BASE_DIR)` y asignación en el briefing de `memory_summary`, `repeated_alerts`, `new_alerts`, `resolved_alerts`, `strategy_changed`, `overall_status_changed`, `attention_trend`, `previous_snapshot_found`, `action_shift`.
- **agents/agent_07_report.py**: lectura de los campos de memoria; bloque "MEMORIA RECIENTE DE REVMAX" en el prompt con memory_summary, repeated_alerts, new_alerts, resolved_alerts, strategy_changed, overall_status_changed, attention_trend, action_shift; regla MEMORIA para mencionar repeated/resolved, strategy_changed, attention_trend y no inventar memoria.
- **tests/test_intelligence_memory.py** (nuevo): tests para primera corrida sin previo, misma alerta repeated_alerts, nueva alerta new_alerts, alerta resuelta resolved_alerts, cambio de strategy_label, cambio de derived_overall_status, attention_trend worsening/improving/stable, _hotel_slug, _build_short_summary, compare_with_previous(None).

---

## 3. CAMBIOS IMPLEMENTADOS

- **Snapshot:** hotel_name, timestamp (ISO UTC), strategy_label, derived_overall_status, consolidated_price_action, alert_types (lista), high_alert_count, critical_alert_count, market_signal_types, recommended_action_types, top_notification_types, short_summary. Persistencia en `data/intelligence_history/<hotel_slug>/snapshot_<timestamp>.json`.
- **Comparación:** repeated_alerts = intersección de alert_types; new_alerts = actual no en previo; resolved_alerts = previo no en actual; repeated_notifications = intersección de top_notification_types; strategy_changed y overall_status_changed por comparación de valores; action_shift = "prev_action -> curr_action" si cambió la acción consolidada; attention_trend = worsening | improving | stable según STATUS_ORDER y conteo de critical+high alerts.
- **Orden en build_memory_bundle:** primero se carga el snapshot previo (si existe), luego se compara con el briefing actual, después se guarda el snapshot de la corrida actual, y se construye memory_summary.
- **Orchestrator:** Tras notification_logic se llama build_memory_bundle y se añaden al briefing los nueve campos indicados.
- **Report:** Bloque MEMORIA RECIENTE y regla para repeated_alerts (persistencia), resolved_alerts (mejora), strategy_changed, attention_trend (tono) y no inventar memoria.

---

## 4. CÓDIGO COMPLETO

### intelligence_memory.py

El archivo completo está en el workspace: cabecera, STATUS_ORDER, ATTENTION_TREND_VALUES, _hotel_slug, _history_dir, _build_short_summary, _snapshot_from_briefing, save_snapshot, load_previous_snapshot, compare_with_previous, _build_memory_summary, build_memory_bundle.

### Cambios en orchestrator.py

**Import:**
```python
from intelligence_memory import build_memory_bundle
```

**Tras el bloque de notification_priority_counts en run_full_analysis:**
```python
    memory_bundle = build_memory_bundle(briefing, hotel_name, _ORCH_BASE_DIR)
    briefing["memory_summary"] = memory_bundle["memory_summary"]
    briefing["repeated_alerts"] = memory_bundle["repeated_alerts"]
    briefing["new_alerts"] = memory_bundle["new_alerts"]
    briefing["resolved_alerts"] = memory_bundle["resolved_alerts"]
    briefing["strategy_changed"] = memory_bundle["strategy_changed"]
    briefing["overall_status_changed"] = memory_bundle["overall_status_changed"]
    briefing["attention_trend"] = memory_bundle["attention_trend"]
    briefing["previous_snapshot_found"] = memory_bundle["previous_snapshot_found"]
    briefing["action_shift"] = memory_bundle.get("action_shift")
```

**En run_fast_demo:** el mismo bloque tras notification_priority_counts y antes de full_analysis.

### Cambios en agents/agent_07_report.py

**Variables del briefing:** memory_summary, repeated_alerts, new_alerts, resolved_alerts, strategy_changed, overall_status_changed, attention_trend, previous_snapshot_found, action_shift.

**Bloque en el prompt:** "MEMORIA RECIENTE DE REVMAX" con previous_snapshot_found, memory_summary, repeated_alerts, new_alerts, resolved_alerts, strategy_changed, overall_status_changed, attention_trend, action_shift.

**Regla:** "MEMORIA: Si hay repeated_alerts, menciónalo como persistencia del problema. Si hay resolved_alerts, menciónalo como mejora. Si strategy_changed, explícalo en una frase. Si attention_trend es worsening, el tono debe reflejar empeoramiento; si improving, reflejar mejora. No inventes memoria fuera de la generada por código."

### tests/test_intelligence_memory.py

El archivo completo está en el workspace: 12 tests (primera corrida, repeated_alerts, new_alerts, resolved_alerts, strategy_changed, overall_status_changed, attention_trend worsening/improving/stable, _hotel_slug, _build_short_summary, compare_with_previous None). Los tests usan tempfile.mkdtemp() como base_path para no escribir en data/ real.

---

## 5. EJEMPLOS REALES DE MEMORIA / COMPARACIÓN

- **Primera corrida:** previous_snapshot_found False, memory_summary "No hay corrida previa para X; esta es la primera vez que se guarda memoria.", repeated_alerts [], new_alerts [], resolved_alerts [], attention_trend "stable".

- **Persistencia de paridad:** Corrida 1 con PARITY_VIOLATION, corrida 2 con PARITY_VIOLATION → repeated_alerts ["PARITY_VIOLATION"], memory_summary incluye "Persisten las alertas: PARITY_VIOLATION."

- **Nueva alerta:** Corrida 1 con LOW_VISIBILITY, corrida 2 con LOW_VISIBILITY y DEMAND_COLLAPSE → new_alerts ["DEMAND_COLLAPSE"], memory_summary incluye "Nuevas alertas: DEMAND_COLLAPSE."

- **Alerta resuelta:** Corrida 1 con PARITY_VIOLATION y LOW_VISIBILITY, corrida 2 solo con LOW_VISIBILITY → resolved_alerts ["PARITY_VIOLATION"], memory_summary incluye "Alertas resueltas desde la corrida anterior: PARITY_VIOLATION."

- **Cambio de estrategia:** Corrida 1 strategy_label BALANCED, corrida 2 DEFENSIVE → strategy_changed True, memory_summary "La estrategia ha cambiado respecto a la corrida anterior."

- **attention_trend worsening:** Corrida 1 derived_overall_status stable y 0 critical/high, corrida 2 status alert y 1 critical → attention_trend "worsening", memory_summary "Tendencia de atención: empeoramiento (más alertas o estado más grave)."

- **attention_trend improving:** Corrida 1 status alert y 2 critical+high, corrida 2 status stable y 0 → attention_trend "improving", memory_summary "Tendencia de atención: mejora (menos alertas o estado mejor)."

- **action_shift:** Corrida 1 consolidated_price_action hold, corrida 2 raise → action_shift "hold -> raise", memory_summary "Cambio de acción consolidada: hold -> raise."

---

## 6. LÍMITES DEL SISTEMA

- Persistencia es solo JSON en disco; no hay base de datos SQL ni agregaciones por semanas/meses. El "previo" es únicamente el último snapshot por hotel.
- La comparación es solo con la corrida inmediatamente anterior; no se analizan N corridas atrás ni patrones temporales avanzados.
- No hay analítica avanzada temporal, gráficos, dashboard nuevo ni ML.
- El snapshot guarda tipos (alert_types, etc.), no el detalle completo de cada alerta/señal; suficiente para comparación semántica simple.
- Si se borra la carpeta data/intelligence_history/<hotel_slug>/, se pierde el histórico; no hay réplica ni backup automático.
- attention_trend se basa en STATUS_ORDER y en la suma critical_alert_count + high_alert_count; criterios fijos por código.
