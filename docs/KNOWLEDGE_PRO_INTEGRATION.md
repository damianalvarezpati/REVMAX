# Integración knowledge → motor determinista PRO

> Gobernanza Dojo y límites: [DOJO_ROLE_AND_PRINCIPLES.md](./DOJO_ROLE_AND_PRINCIPLES.md).

## Reglas integradas (desde `data/knowledge/candidate_rules.json`)

| ID | Soporte | Origen dataset / artefacto | Efecto en PRO |
|----|---------|----------------------------|---------------|
| **HB-001** | strong | `demand_patterns` + `proposed_buckets_summary.empirical_lead_time_buckets_cancel_rate` | Modula `raise_score` y `confidence` según `lead_time_days`; guardrails si ventana larga. |
| **CT-001** | strong | `pricing_context_patterns` (ratio fin de semana) | Si `weekend_context=true`: línea en `reasons` + hasta +1 pp en rango sugerido de **raise** (tope conservador). |
| **RV-001** | strong | `reputation_patterns` (alineación reviewer vs media hotel) | Si hay `reviewer_avg_score_0_10` y `hotel_avg_review_0_10`: penaliza `confidence` y añade guardrail por divergencia. |
| **AB-001** | partial | `pricing_context_patterns` / Airbnb price–rating | Refuerzo moderado: precio alto + reputación débil → `lower_score`+3; precio bajo + reputación sólida → `raise_score`+2. |
| **OTA-001** | partial | `compset_proxy_patterns` | Si `ota_search_distance_km` presente: −1 `confidence`, `reason` marcada como **secondary** (no driver de precio). |

## Reglas explícitamente **no** integradas

| ID | Motivo |
|----|--------|
| **EVT-001** | `support: hypothetical` — excluida por filtro en `revmax_knowledge_pro.APPLICABLE_RULE_IDS` (solo `strong` / `partial`). |
| Buckets `visibility_proxy` / `event_pressure_proxy` marcados hypothetical en JSON | No mapeados a señales operativas; sin evidencia suficiente en este repo. |

## Trazabilidad

- Salida `knowledge_applied[]`: `{ id, support, source, signal }`.
- `reasons` incluyen prefijos `HB-001[strong]`, `AB-001[partial]`, `OTA-001[partial, secondary]`, etc.
- `signals_used` expone campos opcionales: `lead_time_days`, `weekend_context`, `reviewer_avg_score_0_10`, `hotel_avg_review_0_10`, `ota_search_distance_km`.

## Archivos

- Lógica: `revmax_knowledge_pro.py`
- Entrada señales: `decision_rules.build_signals_from_pipeline` + `normalize_signals` passthrough
- Orquestación: `decision_rules_pro.decide_pro`
