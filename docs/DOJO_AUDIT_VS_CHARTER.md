# Auditoría del Dojo vs charter y Definition of Done

**Fecha:** 2026-03-14  
**Criterios:** [DOJO_ROLE_AND_PRINCIPLES.md](./DOJO_ROLE_AND_PRINCIPLES.md), [DOJO_DEFINITION_OF_DONE.md](./DOJO_DEFINITION_OF_DONE.md)  
**Método:** revisión del estado **real** del código y artefactos (no intención documental).

---

## 1. Resumen ejecutivo

El Dojo **backend** (Knowledge Inputs, Refresh, Balancing, Validation Debt, contrato `accept-observed`) está **alineado en gran parte** con el charter: trazabilidad, penalización por deuda, refresh sin auto-aceptación, selección dinámica de áreas, inbox operativo persistido y API de actualización de tareas.

El **cierre operativo end-to-end** falla el estándar del charter en el punto más visible: la **UI Dojo (`frontend-v0/app/dojo/page.tsx`)** sigue usando **casos mock** (`trainingCases`) para el flujo principal de revisión; **no** consume `qa_runs` reales ni ofrece acciones sobre la bandeja de deuda (`POST /api/dojo/validation-inbox/tasks/...` no está integrado en el frontend). Por tanto el Dojo **no puede considerarse “sensei operativo” en producto** hasta que la operadora cierre tareas y veredictos desde el mismo lugar que ve el estado.

**Veredicto global del producto Dojo:** **no aprobado** como conjunto; **aprobado con parches menores** en submódulos de servidor/datos; **no aprobado** en UI y bucle humano completo.

---

## 2. Auditoría por submódulo

### 2.1 Knowledge Inputs

| Criterio (charter / DoD) | Estado real | Gaps / riesgos |
|--------------------------|-------------|----------------|
| Radiografía por área, scores explícitos | `compute_knowledge_inputs` + `scoring_notes` | Riesgo: complejidad alta; regresiones solo detectables por tests |
| Deuda penaliza y puede bloquear madurez | `apply_validation_debt_to_area_score`, campos por área | Parcial: umbrales en config; hay que vigilar falsos positivos si el inbox se llena de tareas auto-generadas |
| Equilibrio de conocimiento enriquece áreas | `enrich_areas_with_knowledge_balance` | Cumple |
| Honestidad / no inflar sin linkage | Bonus `accepted_knowledge` acotado por pesos | Cumple en código |

**Veredicto:** **approved with minor patch**  
**Parches menores:** tests de regresión para fórmulas cuando cambien; revisión periódica de generación masiva de tareas que disparen penalización.

---

### 2.2 Knowledge Refresh

| Criterio | Estado real | Gaps / riesgos |
|----------|-------------|----------------|
| No auto-aceptar conocimiento | Observaciones en cola; `accepted` vacío en auto | Cumple |
| Selección dinámica de áreas | `select_areas_for_refresh` si `knowledge_balancing.use_dynamic_area_selection` | Cumple (configurable) |
| Observaciones → política (inbox) | `sync_validation_inbox(..., observations=observed_all)` post-run | Cumple |
| DoD: observaciones no huérfanas | Tareas `refresh_observation` generadas | Parcial: cierre sigue siendo manual (API); sin UI |

**Veredicto:** **approved with minor patch**  
**Riesgo:** si nadie cierra tareas, inbox crece y penaliza scores sin acción en producto.

---

### 2.3 Validation Debt / Dojo Inbox

| Criterio | Estado real | Gaps / riesgos |
|----------|-------------|----------------|
| Deuda operativa, no sugerencia | `data/dojo/validation_inbox.json`, métricas globales y por área | Cumple en backend |
| Tareas con vínculos y prioridad | `dojo_validation_debt.py` genera desde reglas, QA, mismatches, refresh | Parcial: casos QA usan `area_key` heurístico; puede desalinear tareas |
| Cerrar tareas | `POST /api/dojo/validation-inbox/tasks/{task_id}` | API existe |
| DoD: pending críticas done/dismissed con trazabilidad | `dismissed` sin campo obligatorio `dismiss_reason` en esquema | **Gap:** motivo de dismiss no forzado |

**Veredicto:** **approved with minor patch**  
**Bloqueo producto:** sin UI que llame a la API, el DoD de inbox **no es cerrable** desde el flujo principal del operador.

---

### 2.4 Knowledge Balancing

| Criterio | Estado real | Gaps / riesgos |
|----------|-------------|----------------|
| Reparto no uniforme hacia áreas débiles | Softmax + clusters + refresh usa orden por prioridad | Cumple |
| Charter: priorizar esfuerzo | Integrado en refresh y métricas en inputs | Cumple |

**Veredicto:** **approved with minor patch** (validar tuning en producción; no bloqueante conceptual).

---

### 2.5 Candidate generation (training candidates / refresh)

| Criterio | Estado real | Gaps / riesgos |
|----------|-------------|----------------|
| Material de juicio con contexto | JSON en `data/dojo/training_candidates/` desde refresh | Parcial: candidatos no cierran automáticamente tareas de deuda |
| Ligados a área | `area_key` en caso | Cumple |
| Charter: vehículos de juicio ligados a reglas | **No** siempre hay `linked_rule_id` en candidato | **Gap** respecto a “material anclado” |

**Veredicto:** **not approved**  
**Motivo:** generación existe; **cierre del ciclo** (validación → promoción → reducción de deuda) no está cableado al inbox ni al ledger de forma explícita.

---

### 2.6 Human validation

| Criterio | Estado real | Gaps / riesgos |
|----------|-------------|----------------|
| Casos en `qa_runs` con veredicto cuando el flujo exige | `qa_registry`, `apply_human_review`; API `POST /api/qa/save-validation` desde jobs | **Parcial:** guardado ligado a **job de análisis**, no al flujo Dojo UI |
| Tareas `validation_case` para casos sin veredicto | Generadas en `sync_validation_inbox` | Cumple generación |
| Al guardar veredicto → tarea inbox correspondiente **done** | **No implementado** | **Gap crítico DoD** |

**Veredicto:** **not approved** (como bucle completo).  
**Backend aislado:** **approved with minor patch** (faltan hooks inbox ↔ QA).

---

### 2.7 Integration with decision engine (PRO)

| Criterio | Estado real | Gaps / riesgos |
|----------|-------------|----------------|
| Dojo no sustituye PRO; vigila alineación | `engine_rule_ids` / hooked en Knowledge Inputs; `decision_review` en inbox | Cumple dirección |
| Reglas críticas sin cambios silenciosos | Promoción vía `accept-observed` con trazabilidad | Cumple para conocimiento aceptado; **PRO** sigue siendo código aparte |

**Veredicto:** **approved with minor patch** (documentar en PR cualquier cambio PRO junto a ledger/DoD).

---

### 2.8 Dojo UI / operativa

| Criterio | Estado real | Gaps / riesgos |
|----------|-------------|----------------|
| UI como visor del estado real del sistema | Carga `getKnowledgeInputs()` (scores, refresh, inbox preview) | **Parcial** |
| Flujo principal de revisión | **`trainingCases` mock** (`@/lib/mock-data`) | **Incumple** charter (“no solo pantalla”; casos no son el backlog real) |
| Acciones de inbox (done/dismiss) | **No** en `frontend-v0` (grep sin `validation-inbox`) | **Incumple** DoD operable |

**Veredicto:** **not approved**

---

## 3. Checklist global (estado actual)

| Elemento | Estado |
|----------|--------|
| Charter + DoD documentados | **done** |
| Knowledge Inputs + debt + balancing en API | **done** |
| Knowledge Refresh + sync inbox | **done** |
| Inbox persistido + métricas + API de tareas | **done** |
| Accept-observed con contrato estricto | **done** |
| Selección dinámica de áreas en refresh | **done** (config) |
| `qa_runs` generados desde jobs + registry | **partial** |
| Tareas inbox cerradas desde producto | **missing** |
| Veredicto humano → cierre automático de tarea relacionada | **missing** |
| UI Dojo con casos reales + backlog accionable | **missing** |
| Candidatos refresh con vínculo explícito regla/deuda | **partial** |
| DoD “observaciones no huérfanas” sin acción humana | **blocked** (por UI + cierre de tareas) |

---

## 4. Bloqueos reales

1. **No hay superficie de producto** que ejecute el DoD de inbox (marcar tareas done/dismissed con trazabilidad desde la misma UI donde se ve la deuda).
2. **El flujo de revisión principal del Dojo** usa datos **mock**, no `qa_runs` ni tareas del inbox — desalineación directa con el charter.
3. **Sin hook** veredicto QA / guardado de caso → actualización de tarea `validation_case` → **DoD checklist de validación humana no se puede marcar en verdad** sin trabajo manual fuera de banda (API/curl).

---

## 5. Orden de cierre recomendado (sin abrir piezas nuevas)

1. **Primero — Dojo UI / operativa (mínimo viable)**  
   - Sustituir o **complementar** el flujo mock: listar casos reales (`GET /api/qa/cases` o equivalente) **o** bandeja inbox como lista de trabajo.  
   - Botones que llamen a `POST /api/dojo/validation-inbox/tasks/{id}` con `status` y, si se exige DoD, `dismiss_reason` en backend.  
   **Motivo:** sin esto, el resto del Dojo queda “correcto en servidor pero no operable”.

2. **Segundo — Hook humano ↔ inbox**  
   - Al guardar `human_verdict` en un caso cuyo `linked_case_id` coincide con una tarea `validation_case`, marcar tarea **done** (o documentar proceso manual explícito).  
   **Motivo:** cerrar el DoD de validación humana sin mentira.

3. **Tercero — Candidate generation**  
   - Añadir en JSON de candidatos referencias explícitas (`linked_rule_id`, `task_id` opcional) y documentar flujo “revisar candidato → cerrar deuda relacionada”.  
   **Motivo:** alinear charter de “material de juicio” sin inventar nuevos subsistemas.

4. **No tocar todavía**  
   - Reescrituras grandes de scoring, nuevos tipos ML, o nuevas fuentes de scraping; **hasta** que el bucle 1–2 esté cerrado o explícitamente aceptado como deuda aceptada.

---

## 6. Tabla de veredictos

| Submódulo | Veredicto |
|-----------|-----------|
| Knowledge Inputs | **approved with minor patch** |
| Knowledge Refresh | **approved with minor patch** |
| Validation Debt / Inbox (backend) | **approved with minor patch** |
| Knowledge Balancing | **approved with minor patch** |
| Candidate generation | **not approved** |
| Human validation (E2E) | **not approved** |
| Decision engine integration | **approved with minor patch** |
| Dojo UI / operativa | **not approved** |

---

## 7. Referencias de código (auditoría reproducible)

- `knowledge_inputs.py` — sync inbox, penalización, balancing  
- `knowledge_refresh.py` — selección dinámica, `sync_validation_inbox`  
- `dojo_validation_debt.py` — tareas, métricas  
- `knowledge_balancing_engine.py` — prioridades  
- `frontend-v0/app/dojo/page.tsx` — `trainingCases` + `getKnowledgeInputs`  
- `admin_panel.py` — `/api/dojo/validation-inbox`, `/api/qa/save-validation`  

---

*Este documento es el resultado de la auditoría; no sustituye tests automatizados ni revisión de producción.*

---

## Apéndice — Cierre MVP (post–auditoría inicial)

Implementado para acotar los bloqueos “no operable desde producto” y “sin hook QA ↔ inbox”:

- **UI:** bloque **Operativa — bandeja Dojo** en `frontend-v0/app/dojo/page.tsx` con `GET /api/dojo/validation-inbox` y `POST .../tasks/{id}` (Hecho / Descartar + motivo opcional al descartar).
- **Backend:** `mark_validation_tasks_done_for_case_path` tras `apply_human_review` en `POST /api/qa/save-validation` y en `operator_console.data_loader.apply_validation`.

*Re-auditoría recomendada tras estabilizar en producción.*
