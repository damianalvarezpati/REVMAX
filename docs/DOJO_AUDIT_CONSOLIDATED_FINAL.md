# Auditoría consolidada final — Dojo (RevMax)

**Fecha:** 2026-03-14 (consolidada; estado referido al código tras cierres MVP, deuda dismiss/done, y UI bandeja).  
**Criterio:** SHOKUN — exigente, sin inventar problemas. No sustituye pruebas en producción con usuarios reales.

**Nota:** `docs/DOJO_AUDIT_VS_CHARTER.md` conserva el histórico; varios bloques listados allí como “missing” quedaron **cerrados** en iteraciones posteriores (véase apéndice de ese doc y este informe).

---

## 1. Veredicto por submódulo

### 1.1 Knowledge Inputs

| Aspecto | Estado real |
|--------|-------------|
| Qué va bien | Snapshot por API; scores por área; integración con deuda efectiva, balancing, ledger; `scoring_notes` explícitos. |
| Patch menor | Vigilar regresiones si cambian fórmulas (tests existentes ayudan; snapshot manual ocasional). |
| **Veredicto** | **approved with minor patch** |

### 1.2 Knowledge Refresh

| Aspecto | Estado real |
|--------|-------------|
| Qué va bien | No auto-acepta; observaciones trazadas; `sync_validation_inbox`; selección dinámica de áreas (config); cap de candidatos por área/run. |
| Patch menor | Monitoreo de volumen de observaciones si el índice de datasets crece mucho. |
| **Veredicto** | **approved with minor patch** |

### 1.3 Validation Debt / Inbox

| Aspecto | Estado real |
|--------|-------------|
| Qué va bien | Inbox persistido; generación desde reglas, QA, mismatches, refresh; API de tareas; **dismiss ≠ done** (residual + `honest_validation_closure_score`); `validation_debt_impact` extendido; métricas globales y por área. |
| Patch menor | “Hecho” sin evidencia de revisión sigue siendo posible (riesgo operativo, no bug); opcional: política o longitud mínima de motivo dismiss en UI. |
| **Veredicto** | **approved with minor patch** |

### 1.4 Knowledge Balancing

| Aspecto | Estado real |
|--------|-------------|
| Qué va bien | Enriquecimiento de áreas; priorización coherente con refresh; snapshot. |
| Patch menor | Tuning de targets en producción según feedback (no bloqueo conceptual). |
| **Veredicto** | **approved with minor patch** |

### 1.5 Candidate generation (refresh → training_candidates)

| Aspecto | Estado real |
|--------|-------------|
| Qué va bien | Vínculos: `source_reference`, reglas/hipótesis, `linked_task_ids`, `reason`, `required_review_type`, `close_condition`; cap por run/área. |
| Patch menor | Sigue siendo artefacto intermedio (“hold”), no gold cerrado; promoción a ledger/validado sigue siendo proceso consciente, no automático total. |
| **Veredicto** | **approved with minor patch** |

### 1.6 Human validation end-to-end

| Aspecto | Estado real |
|--------|-------------|
| Qué va bien | `save-validation` + `apply_human_review`; `mark_validation_tasks_done_for_case_path`; mismo hook en operator console; tareas `validation_case` alineadas por path. |
| Patch menor | Flujo principal de veredicto sigue siendo Analysis / operator console, no un formulario embebido en Dojo UI (aceptable si la bandeja es el backlog y Analysis el veredicto). |
| **Veredicto** | **approved with minor patch** |

### 1.7 Integración decision engine (PRO)

| Aspecto | Estado real |
|--------|-------------|
| Qué va bien | `engine_rule_ids` / hooked en Knowledge Inputs; tareas `decision_review` cuando falta integración; Dojo no sustituye al motor. |
| Patch menor | Cualquier cambio PRO debe seguir documentado junto a conocimiento/ledger (proceso, no fallo del Dojo). |
| **Veredicto** | **approved with minor patch** |

### 1.8 Dojo UI / operativa

| Aspecto | Estado real |
|--------|-------------|
| Qué va bien | Con `NEXT_PUBLIC_REVMAX_API_URL`: bandeja real, métricas por tipo, áreas bloqueadas, Hecho/Descartar/Revisar, Caso/Regla (JSON), preview Caso solo si parece path; mock relegado sin API. |
| Patch menor | Cabecera mezcla EN/ES; sin orden por `priority`; JSON crudo para Caso/Regla (fricción no técnica). |
| **Veredicto** | **approved with minor patch** |

---

## 2. Estado global del Dojo

| Pregunta | Respuesta |
|----------|-----------|
| ¿Funcionalmente cerrado como **sistema operativo** (backlog + deuda + QA + métricas)? | **Sí**, con API configurada y flujo Analysis/operator para veredictos. |
| ¿Bloqueo serio restante? | **No** del tipo “no se puede operar el Dojo”. Quedan **flecos de producto/UX** y **honestidad del Hecho** como riesgo operativo, no como bug de integración. |
| ¿Nivel vs charter inicial? | **Subido**: UI bandeja real, hook QA↔inbox, deuda con integridad dismiss/done, candidatos con contexto. |

**Veredicto global:** **approved with minor patches** (no “approved” pleno solo por detalles de UX/copy, JSON como vista principal, y ausencia de evidencia obligatoria en Hecho).

---

## 3. Patches menores pendientes (por prioridad)

### P1 — Alto impacto / bajo coste

1. **Dojo UI:** alinear copy (ES) en cabecera con la bandeja; ordenar tareas pendientes por `priority` descendente.
2. **Observabilidad:** 1–2 líneas de log en servidor al cerrar tarea inbox (task_id, closure_quality, área) para auditoría sin abrir JSON.

### P2 — Mejora clara, no bloqueante

3. **Dojo UI:** preview legible mínimo (título + campos clave) para Caso/Regla, manteniendo enlace a JSON crudo; o documentar explícitamente que JSON es la vista intencionada para operadores técnicos.
4. **Dismiss:** recordatorio en UI si `needs_revisit` (dismiss sin motivo) — ya marcado en datos; podría mostrarse badge.

### P3 — Nice to have / producción

5. **Knowledge Inputs:** revisión periódica de umbrales `validation_debt_config.json` con datos reales.
6. **Hecho:** política de evidencia (comentario obligatorio, checklist) — solo si el negocio lo exige; evitar scope creep.

---

## 4. Qué **no** reabre líneas (explícito)

- Nuevos scores complejos, ML, scraping masivo, o reescritura grande del motor de análisis.
- Sustituir JSON por UI rica completa (P2 es opcional y mínima).

---

## 5. Referencias rápidas

- Código: `knowledge_inputs.py`, `knowledge_refresh.py`, `dojo_validation_debt.py`, `knowledge_balancing_engine.py`, `admin_panel.py`, `frontend-v0/app/dojo/page.tsx`
- Config: `data/dojo/validation_debt_config.json`
- Práctica previa: `docs/DOJO_PRACTICAL_AUDIT.md` (§3 dismiss=done **obsoleto** respecto al modelo residual actual)
- SHOKUN: `docs/shokun/README.md`

---

*Consolidación para decisión de producto: el Dojo puede considerarse **operativamente cerrado** con **patches menores** pendientes, no con bloqueos estructurales mayores.*
