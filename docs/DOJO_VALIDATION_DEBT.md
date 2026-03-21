# Dojo — Deuda de validación (inbox operativo)

> Marco general: [DOJO_ROLE_AND_PRINCIPLES.md](./DOJO_ROLE_AND_PRINCIPLES.md).

## Principio

La validación humana **no** se modela como recomendación: es **deuda acumulada** y **trabajo pendiente obligatorio** en `data/dojo/validation_inbox.json`. El Dojo expone una bandeja con tareas concretas (`task_id`, tipo, prioridad, vínculos).

## Modelo de datos

| Campo | Uso |
|-------|-----|
| `task_id` | Identificador estable (hash de contexto) |
| `task_type` | `validation_case`, `hypothesis_review`, `rule_review`, `compset_review`, `decision_review`, `legacy_pro_mismatch`, `refresh_observation` |
| `area_key` | Área afectada |
| `priority` | 1–10 |
| `created_at` | ISO UTC |
| `reason` | Motivo operativo (trazable) |
| `linked_case_id` / `linked_hypothesis_id` / `linked_rule_id` | Vínculos |
| `required_for_area_progress` | Si cuenta para bloqueo de madurez |
| `status` | `pending` \| `done` \| `dismissed` |
| `assigned_to` | Opcional |

Config: `data/dojo/validation_debt_config.json`. Divergencias legacy vs PRO: `data/dojo/legacy_pro_mismatches.json` (lista `mismatches`).

## Creación automática

| Origen | Tareas |
|--------|--------|
| `candidate_rules.json` | Hipótesis → `hypothesis_review`; parciales → `rule_review`; regla esperada en área no integrada en PRO → `decision_review` |
| `data/qa_runs/*.json` | Sin `human_verdict` → `validation_case` |
| `legacy_pro_mismatches.json` | Cada ítem → `legacy_pro_mismatch` |
| Knowledge refresh | Observaciones del ciclo → `refresh_observation` (vía `sync_validation_inbox` tras el run) |

`sync_validation_inbox()` se ejecuta al calcular **Knowledge Inputs** y al finalizar **Knowledge Refresh**.

## Impacto en score y madurez

- **`validation_debt_score`** por área (0–100): agrega peso por tipo y prioridad.
- **Penalización** sobre `area_score` (hasta `area_score_penalty_max`) vía `debt_to_penalty_scale`.
- **Bloqueo**: si `required_pending_count` ≥ umbral o `validation_debt_score` ≥ umbral → `area_blocked_by_validation`, techo de score (no “strong” mientras bloqueada) y mensaje en `missing_gaps`.

Campos en cada área: `area_score_before_validation_debt`, `validation_debt_penalty`, contadores de pendientes.

## Métricas

**Por área:** `pending_*_count`, `validation_debt_score`, `area_blocked_by_validation`.

**Globales (`dojo_validation_inbox.global_metrics`):** `dojo_inbox_count`, `overdue_reviews_count`, `areas_blocked_count`, `pending_by_type`.

## API

- `GET /api/dojo/knowledge-inputs` — incluye `dojo_validation_inbox` y métricas por área.
- `GET /api/dojo/validation-inbox` — inbox + métricas completas.
- `POST /api/dojo/validation-inbox/tasks/{task_id}` — body `{ "status": "done"|"dismissed"|"pending", "assigned_to": "..." }`.

## UI

Dojo (`frontend-v0/app/dojo/page.tsx`): bloque **“Bandeja obligatoria — deuda de validación”** y columna de deuda en la tabla de áreas.
