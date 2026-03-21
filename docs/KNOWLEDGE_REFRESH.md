# Knowledge Refresh (daily / nightly)

## Qué hace

- Calcula **Knowledge Inputs** antes y después del ciclo.
- **Prioriza** áreas con `status_label` weak → developing → usable → strong y, dentro de cada grupo, **menor `area_score`**.
- Consulta fuentes **dirigidas**:
  - `MASTER_DATASET_INDEX.json` (paths **nuevos** respecto a `refresh_state.json`, tras bootstrap inicial).
  - Patrones `data/knowledge/*_patterns.json` (cambio de mtime).
  - HTTP solo si `allow_http_fetch` + `http_allowlist` en `knowledge_refresh_config.json`.
  - Script `extract_revmax_knowledge.py` solo si `run_extract_script: true`.
- **`observed_new_data`**: siempre en cola / run log; **no** entra en `accepted_knowledge` solo.
- **`accepted_knowledge`**: solo `POST /api/dojo/knowledge-refresh/accept-observed` con deduplicación por hash.
- Genera **candidatos Dojo** en `data/dojo/training_candidates/*.json`.

## Artefactos

| Archivo | Contenido |
|---------|-----------|
| `data/knowledge/refresh/knowledge_refresh_runs.jsonl` | Una línea JSON por ejecución (completa) |
| `data/knowledge/refresh/latest_refresh_summary.json` | Resumen para UI / API |
| `data/knowledge/refresh/knowledge_area_adjustments.json` | Historial de deltas de score por área |
| `data/knowledge/refresh/observed_queue.jsonl` | Cola append-only de observaciones |
| `data/knowledge/refresh/accepted_knowledge.jsonl` | Solo promociones manuales |
| `data/knowledge/refresh/accepted_hashes.json` | Dedup |
| `data/knowledge/refresh/refresh_state.json` | Paths conocidos + mtimes patrones |

## API

- `POST /api/dojo/knowledge-refresh/run` — body opcional `{ "mode", "area_keys": [] }`
- `GET /api/dojo/knowledge-refresh/latest`
- `POST /api/dojo/knowledge-refresh/accept-observed` — promoción controlada
- `GET /api/dojo/knowledge-inputs` incluye `knowledge_refresh` (último resumen)

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

Tras el refresh se vuelve a ejecutar `compute_knowledge_inputs`. Los deltas suelen ser **0** si no hubo aceptaciones nuevas; suben **`quality_score`** al añadir líneas a `accepted_knowledge.jsonl` (hasta +15 por área acotado).
