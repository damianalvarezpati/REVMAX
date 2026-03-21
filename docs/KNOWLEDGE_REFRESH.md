# Knowledge Refresh (daily / nightly)

## Qué hace

- Calcula **Knowledge Inputs** antes y después del ciclo.
- **Prioriza** áreas con `status_label` weak → developing → usable → strong y, dentro de cada grupo, **menor `area_score`**.
- Consulta fuentes **dirigidas**:
  - `MASTER_DATASET_INDEX.json` (paths **nuevos** respecto a `refresh_state.json`, tras bootstrap inicial).
  - **Nuevos paths** se evalúan contra **todas** las áreas del config; si un dataset encaja en varias, `area_keys_touched` lista todas — no se pierde señal por no estar en el lote priorizado del día.
  - Patrones `data/knowledge/*_patterns.json`: **hash de contenido** (no solo mtime) en `state.pattern_content_hashes` — evita observaciones falsas por touch/save sin cambio real.
  - HTTP solo si `allow_http_fetch` + `http_allowlist` en `knowledge_refresh_config.json`.
  - Script `extract_revmax_knowledge.py` solo si `run_extract_script: true`.
- **`observed_new_data`**: siempre en cola / run log; **no** entra en `accepted_knowledge` solo.
- **`accepted_knowledge`**: solo `POST /api/dojo/knowledge-refresh/accept-observed` con deduplicación por hash y **campos obligatorios de trazabilidad** (ver abajo).
- **Candidatos Dojo**: solo si en el ciclo hubo al menos **una observación relevante** para esa área (`dojo_relevant_observation_kinds` + `dojo_min_relevant_observations`). Sin placeholders vacíos.

## Reglas de calidad (refresh)

| Regla | Descripción |
|--------|-------------|
| Relevancia Dojo | Tipos `dataset_index_path_new`, `pattern_file_changed`, `http_allowlist_fetch` (configurable). El área debe figurar en `area_keys_touched` o `area_key` según el tipo. |
| Patrones | Cambio detectado por **hash de contenido**; primer ciclo solo semilla estado sin observación. |
| Datasets multi-área | `matched_aks` = todas las áreas que matchean el dataset, no solo `to_process`. |
| Aceptación manual | `reason_for_acceptance` con longitud mínima; `linked_rule_or_hypothesis`, `knowledge_type`, `source_reference`, `accepted_by`, `content_hash`; `acceptance_trace_id` UUID en cada línea. |
| Quality score | Bonus desde `accepted_knowledge` **acotado** (máx. puntos en `accepted_quality_scoring`); peso alto solo con `knowledge_type` + `linked_rule_or_hypothesis`; sin linkage fuerte, peso mínimo. |

## Artefactos

| Archivo | Contenido |
|---------|-----------|
| `data/knowledge/refresh/knowledge_refresh_runs.jsonl` | Una línea JSON por ejecución (completa, incluye `funnel`) |
| `data/knowledge/refresh/latest_refresh_summary.json` | Resumen para UI / API + `funnel` + `funnel_metrics` |
| `data/knowledge/refresh/refresh_funnel_metrics.json` | Acumulado funnel + `last_run` |
| `data/knowledge/refresh/knowledge_area_adjustments.json` | Historial de deltas de score por área |
| `data/knowledge/refresh/observed_queue.jsonl` | Cola append-only de observaciones |
| `data/knowledge/refresh/accepted_knowledge.jsonl` | Solo promociones manuales (trazabilidad) |
| `data/knowledge/refresh/accepted_hashes.json` | Dedup |
| `data/knowledge/refresh/refresh_state.json` | Paths conocidos + **hashes de contenido** de patrones |

## Métricas de funnel (artefacto + API)

En `refresh_funnel_metrics.json` / `latest_refresh_summary.json` / `GET /api/dojo/knowledge-refresh/funnel`:

- **observed_total** / **observed_count** (por run en `this_run`)
- **accepted_total** (incrementa en cada accept)
- **acceptance_rate** (accepted_total / max(observed_total, 1))
- **runs_with_delta_count** (runs con algún delta de `area_score` ≠ 0)
- **dojo_candidates_generated_total** / generados en este run
- **dojo_candidates_validated** (archivos `training_candidates` con `dojo_validation_status: "validated"`)
- **runs_with_meaningful_output** (runs con observed>0 o dojo generados)
- **area_score_changes_count** (suma de áreas con delta ≠ 0 acumulada)

## API

- `POST /api/dojo/knowledge-refresh/run` — body opcional `{ "mode", "area_keys": [] }`
- `GET /api/dojo/knowledge-refresh/latest`
- `GET /api/dojo/knowledge-refresh/funnel`
- `POST /api/dojo/knowledge-refresh/accept-observed` — promoción controlada (campos obligatorios de trazabilidad)
- `GET /api/dojo/knowledge-inputs` incluye `knowledge_refresh` (último resumen + `funnel_lifetime` si existe métricas)

## CLI

```bash
python3 knowledge_refresh.py manual
python3 knowledge_refresh.py area demand,events
```

## Cron

```bash
chmod +x scripts/knowledge_refresh_cron.sh
# crontab -e
# 15 3 * * * /ruta/revmax/scripts/knowledge_refresh_cron.sh >> /tmp/revmax_refresh.log 2>&1
```

## Scores

Tras el refresh se vuelve a ejecutar `compute_knowledge_inputs`. Los deltas suelen ser **0** si no hubo aceptaciones nuevas; el bonus de **`quality_score`** por `accepted_knowledge` usa pesos **estrictos** (ver `accepted_quality_scoring` en config) y techo máximo **8** puntos por defecto, no inflación lineal por recuento.
