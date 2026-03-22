# Auditoría práctica — Dojo operativo (uso real)

**Fecha:** 2026-03-14  
**Enfoque:** bandeja de trabajo, no solo arquitectura. Criterio exigente.

---

## 1. Operativa real del Dojo UI

### Claridad de la bandeja
- **Fortalezas:** contadores por tipo, áreas bloqueadas, `task_type` + `area_key` + `requerido`, acciones agrupadas.
- **Debilidades:** rejilla de 8 métricas en pantallas pequeñas añade carga cognitiva; el campo `priority` no se muestra (no se ordena por urgencia); cabecera de página sigue en inglés mientras la bandeja es operativa en español.

### Utilidad de las tareas
- Alta para **operador técnico** que ya entiende tipos (`validation_case`, `hypothesis_review`, etc.).
- Media para **revisor de negocio:** el `reason` es texto sistema, no siempre accionable en un clic.

### Contexto al abrir Caso o Regla
- **Caso:** abre JSON crudo en nueva pestaña — útil para depuración; **fricción** para quien espera resumen o vista “humana”.
- **Regla:** idem (JSON de `candidate_rules.json`) — correcto para revisión técnica; poco amigable para lectura rápida.

### Cerrar / descartar / revisar
- **Hecho / Descartar** con motivo opcional: flujo corto.
- **Revisar:** solo resalta la fila (poca utilidad si ya estás en la lista).
- **Riesgo:** “Descartar” **reduce la deuda igual que Hecho** a efectos de métricas (ambos sacan la tarea del conjunto `pending`). Ver §3.

### Fricción general
- Baja para **cerrar tareas**; media-alta para **entender impacto** sin leer JSON o `validation_inbox.json`.

---

## 2. Calidad real de las tareas generadas

### Utilidad
- **Reglas hipotéticas / parciales / decision_review:** alineadas con riesgo real (motor PRO, compset).
- **validation_case desde QA:** útiles si hay casos sin veredicto; pueden **multiplicarse** con muchos ficheros en `qa_runs`.
- **refresh_observation:** útil para trazabilidad; el vínculo “Caso” puede apuntar a un `observed_id` que **no es ruta de archivo** → preview puede fallar (404).

### Concretitud
- Razonable en `reason`; no siempre incluye **siguiente acción única** (“qué hacer en los próximos 5 minutos”).

### Ruido
- `merge_generated_into_inbox` evita duplicados por `task_id`; el ruido viene más de **volumen de casos QA** y de **varios candidatos por área** en refresh que repiten el mismo contexto.

### Reducción de validation debt
- Las tareas **pending** alimentan `validation_debt_score` por área; cerrarlas baja el score. Ver §3 sobre **integridad** al descartar sin validar.

---

## 3. Calidad real del cierre de deuda

### Coherencia before / after
- `validation_debt_impact` compara deuda de área **antes y después** de pasar la tarea a `done`/`dismissed`; es **coherente a nivel agregado** por área.
- Si quedan muchas tareas pendientes en el mismo área, el delta puede ser **pequeño** — no es un fallo, es lectura agregada.

### Inflación artificial
- **Sí, posible:** cualquier usuario con API puede marcar **Hecho** o **Descartar** sin prueba de revisión; la deuda baja igual.
- No hay firma de rol ni obligatoriedad de veredicto en Dojo UI para tipos que no son `validation_case`.

### “Madurez falsa”
- **Descartar sin trabajo real** mejora las mismas métricas que cerrar bien → el sistema **no distingue** calidad del cierre en el score.
- **Hecho** sobre tarea mal entendida también baja deuda.

### Vínculo tarea ↔ caso ↔ validación
- **QA:** `mark_validation_tasks_done_for_case_path` tras `save-validation` + matching de rutas es **robusto** para paths equivalentes (`samefile` / normalización).
- **Caso / Regla en UI:** dependen de `linked_*` rellenados en generación; si falta link, el operador no abre contexto.

---

## 4. Calidad real de los candidatos (Knowledge Refresh)

### Contexto
- Mejor que placeholders: `source_reference`, `linked_task_ids`, `reason`, `required_review_type`, `close_condition`, resúmenes en `refresh_context`.
- Sigue siendo un **artefacto intermedio** (p. ej. `consolidated_action: hold`), no un caso de entrenamiento “cerrado” listo para gold sin más pasos.

### Revisabilidad
- **Revisable** por alguien que entiende pipeline y reglas; **pesado** si se espera revisión tipo “caso hotel” completo.

### Utilidad vs cola
- `n_cand` > 1 por área puede **llenar la cola** con variaciones del mismo refresh; ayuda al Dojo solo si alguien **prioriza y valida** candidatos; de lo contrario es ruido acumulado en disco.

---

## 5. Veredicto por bloque

| Bloque | Veredicto |
|--------|-----------|
| **Dojo UI MVP** | **approved with minor patch** |
| **Hook QA ↔ inbox** | **approved** |
| **Candidate generation** | **approved with minor patch** |
| **Validation debt closure** | **not approved** (como garantía de madurez “honesta”; como mecánica operativa, funciona pero es gaming-friendly) |

---

## 6. Parches mínimos recomendados (sin rehacer producto)

1. **Deuda / Descartar:** en `update_task_status`, si `status=dismissed`, **no aplicar** la misma reducción de deuda que `done`, **o** contar `dismissed` aparte en `global_metrics` y en penalización de área (p. ej. dismissed sigue pesando 0.5× hasta auditoría).
2. **UI Caso:** si `linked_case_id` no resuelve a fichero bajo `BASE_DIR`, ocultar “Caso” o mostrar tooltip “ID de observación, sin preview”.
3. **Candidatos:** cap duro o dedupe por `(area_key, run_id)` para no generar N JSON casi idénticos en el mismo run (o bajar `n_cand` cuando `rel_obs` no cambia).
4. **UI:** mostrar `priority` numérico o ordenar pendientes por `priority` desc; una línea de copy en español en cabecera alineada con la bandeja.

---

## Actualización — integridad de deuda (post-auditoría)

Implementado: **dismissed** deja **residual** en `effective_validation_debt` (config `dismissed_residual_*`); **done** elimina el peso pendiente sin residual. Métricas: `debt_resolved_count`, `debt_dismissed_count`, `honest_validation_closure_score` por área. Trazabilidad: `closure_quality`, `close_reason`, `needs_revisit` si dismiss sin motivo. Ver `validation_debt_config.json` v2.

---

*Auditoría basada en comportamiento del sistema y revisión de código de rutas críticas; validación en producción con usuarios reales sigue siendo recomendable.*
