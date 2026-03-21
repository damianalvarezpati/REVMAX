# Dojo — Knowledge Inputs

> **Rol del Dojo en RevMax:** ver [DOJO_ROLE_AND_PRINCIPLES.md](./DOJO_ROLE_AND_PRINCIPLES.md). Criterios de cierre: [DOJO_DEFINITION_OF_DONE.md](./DOJO_DEFINITION_OF_DONE.md).

## Modelo de datos (por área)

Cada área expuesta en la API y en `knowledge_inputs_snapshot.json` incluye:

| Campo | Descripción |
|-------|-------------|
| `area_key` | Clave estable (`demand`, `reputation`, …) |
| `area_name` | Etiqueta humana |
| `datasets_count` | Datasets en `MASTER_DATASET_INDEX.json` que encajan con la área |
| `datasets_rows_approx_sum` | Suma de filas (tope por dataset para robustez) |
| `real_cases_count` | Reparto proporcional de casos `qa_runs` con `human_score` |
| `synthetic_cases_count` | Parte equitativa del mock `trainingCases` (config) |
| `validated_cases_count` | `ledger.human_validations` + `real_cases_count` |
| `rules_supported_count` | Reglas `strong`+`partial` en `candidate_rules.json` cuyo `applies_to` casa |
| `hypotheses_pending_count` | Reglas `hypothetical` en el área |
| `coverage_score` | 0–100 |
| `quality_score` | 0–100 |
| `validation_score` | 0–100 |
| `model_readiness_score` | 0–100 |
| `area_score` | Combinación ponderada |
| `status_label` | `weak` / `developing` / `usable` / `strong` |
| `missing_gaps` | Lista explícita de carencias |
| `suggested_actions` | Acciones concretas (datasets, scraping, validación, mapping, reglas) |

## Fuentes

- `data/knowledge/knowledge_areas_config.json` — mapeo área ↔ datasets ↔ patrones ↔ reglas motor
- `data/knowledge/candidate_rules.json`
- `data/knowledge/*_patterns.json`
- `data/datasets/MASTER_DATASET_INDEX.json`
- `data/knowledge/dojo_validation_ledger.json`
- `data/qa_runs/*.json`

## Lógica de scoring (no decorativa)

Definición en `knowledge_inputs.compute_knowledge_inputs` → `scoring_notes` en la respuesta JSON.

Resumen:

1. **coverage**: satura con número de datasets (exponencial); bonus acotado por archivos de patrones presentes.
2. **quality**: fuerza de reglas (strong > partial; hypothetical no suma) + factor log(filas de datasets del área).
3. **validation**: validaciones en ledger + reparto de QA humano vs objetivo blando por área + peso extra por `hypotheses_promoted`.
4. **model_readiness**: reglas listadas en config como integradas en PRO (`engine_integrated_rule_ids`) frente a las esperadas por área; sin IDs de motor, techo bajo salvo reglas soportadas/patrones.

**area_score** = `0.28*coverage + 0.27*quality + 0.22*validation + 0.23*readiness`

## Cómo cambia el score dinámicamente

| Evento | Efecto |
|--------|--------|
| Nuevo dataset indexado (flags correctos) | ↑ `datasets_count`, ↑ coverage (+ quality por filas) |
| Nuevo `*_patterns.json` o extracción | ↑ coverage (bonus patrones) |
| Nueva regla strong/partial en `candidate_rules` | ↑ quality; si está en `engine_rule_ids` del área, puede ↑ readiness al cablear en código |
| Validación humana (`/api/qa/save-validation`) | ↑ reparto QA → validation |
| `POST /api/dojo/validation-ledger` | ↑ `human_validations` o `hypotheses_promoted` por área |
| Integrar regla en `revmax_knowledge_pro` + `engine_integrated_rule_ids` | ↑ readiness |

## API

- `GET /api/dojo/knowledge-inputs` — payload completo + escribe `data/knowledge/knowledge_inputs_snapshot.json`
- `POST /api/dojo/validation-ledger` — body: `{ "area_key", "delta_human_validations", "delta_hypotheses_promoted" }`

## UI

- `frontend-v0/app/dojo/page.tsx` — panel compacto si `NEXT_PUBLIC_REVMAX_API_URL` apunta al admin panel.
