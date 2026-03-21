# Knowledge Balancing Engine

## Propósito

Equilibrio **activo** del mapa de conocimiento del Dojo: no reparto uniforme. El sistema:

- Detecta áreas débiles (gap vs target).
- Asigna **más esfuerzo relativo** (share) a cerrar brechas.
- Coloca áreas fuertes en **mantenimiento** (sin sobre-invertir).
- Usa **clusters** (p. ej. pricing_context ↔ compset ↔ ota_visibility) para sugerir **validación humana cruzada** cuando un miembro del cluster tiene hueco alto.
- Alimenta el **Nightly Knowledge Refresh** con selección dinámica de áreas y multiplicador de candidatos Dojo según gap.

No sustituye el juicio humano: las reglas son explícitas y trazables (`knowledge_balancing_config.json`).

## Archivos

| Archivo | Rol |
|---------|-----|
| `knowledge_balancing_engine.py` | Cálculo de balance por área, selección de áreas para refresh, multiplicador Dojo |
| `data/knowledge/knowledge_balancing_config.json` | Targets, umbrales growth/maintenance, clusters, pesos |
| `data/knowledge/knowledge_balance_snapshot.json` | Snapshot opcional (cuando `compute_knowledge_inputs` escribe) |

## Campos por área (`knowledge_balance`)

| Campo | Significado |
|-------|-------------|
| `current_area_score` | `area_score` actual |
| `target_area_score` | Objetivo según `status_label` o global |
| `knowledge_gap_score` | `max(0, target - current)` acotado |
| `growth_priority` | 0–100 (posición relativa de prioridad de crecimiento) |
| `mode` | `growth` \| `monitor` \| `maintenance` |
| `growth_mode` / `maintenance_mode` | Banderas derivadas |
| `recommended_effort_share` | Parte del esfuerzo global (softmax sobre prioridades; suma ≈ 1) |
| `human_validation_priority` | 0–1 (sube con gap y déficit de `validation_score`) |
| `why_this_area_needs_attention` | Texto breve trazable |
| `suggested_data_actions` | Ingesta, scraping acotado, extract, etc. |
| `suggested_human_validation_actions` | Dojo / QA / ledger; refuerzo en clusters |
| `recommended_actions` | Resumen operativo |

## Integración

- **Knowledge Inputs** (`compute_knowledge_inputs`): enriquece cada entrada de `areas[]` y añade `knowledge_balance_summary` en la raíz.
- **Knowledge Refresh** (`run_knowledge_refresh`): si `knowledge_balancing.use_dynamic_area_selection` es true, el orden de trabajo nocturno sigue `growth_priority` + gap (no solo status). Los candidatos Dojo usan multiplicador acotado por gap/modo.
- **API** `GET /api/dojo/knowledge-inputs`: incluye el bloque anterior.

## Reparto de esfuerzo (resumen)

1. Prioridad cruda: función del gap (exponente), déficits de validación/cobertura/readiness, epsilon uniforme.
2. **Cluster boost**: si algún par del cluster tiene gap alto, sube la prioridad de refuerzo en todo el cluster.
3. **Softmax** → `recommended_effort_share`.
4. **Modo**: umbrales `growth_gap_min` / `maintenance_gap_max`.

## Validación humana como refuerzo

- `human_validation_priority` sube cuando el gap es grande o `validation_score` es bajo.
- Notas de **validación cruzada** si otro área del mismo cluster tiene brecha ≥ 15.
