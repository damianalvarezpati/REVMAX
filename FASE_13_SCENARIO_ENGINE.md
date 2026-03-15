# FASE 13 — Scenario / Recommendation Engine

## 1. PROBLEMA QUE RESUELVE SCENARIO ENGINE

RevMax ya prioriza oportunidades y acciones (Value Prioritization Engine) pero no comparaba de forma explícita escenarios de postura (raise, hold, lower) ni explicaba qué postura parece más razonable o defendible.

El **Scenario Engine** añade una comparación explícita entre los tres escenarios, generada por código (no por el LLM), con support_score, risk_score, net_score, verdict y razón por escenario, de modo que RevMax pueda decir qué escenario es más consistente con las señales, cuál tiene más riesgo y cuál parece más defendible y por qué. No reemplaza `consolidate()`; lo complementa.

---

## 2. ARCHIVOS MODIFICADOS

| Archivo | Acción |
|---------|--------|
| `scenario_engine.py` | **Creado** — build_scenario_assessment(briefing) |
| `orchestrator.py` | **Modificado** — integración tras Value Prioritization |
| `agents/agent_07_report.py` | **Modificado** — bloque ESCENARIOS EVALUADOS POR REVMAX |
| `tests/test_scenario_engine.py` | **Creado** — tests unitarios |
| `FASE_13_SCENARIO_ENGINE.md` | **Creado** — esta documentación |

No tocados: job_schema, job_state, job_runtime, job_watchdog, job_recovery, job_observability, admin_panel, analysis_runner. No rotos: consolidate, Strategy, Alert, Market Signals, Decision Engine, Notification Logic, Intelligence Memory, Opportunity Engine, Impact Engine, Executive Output, Value Prioritization, tests existentes.

---

## 3. CAMBIOS IMPLEMENTADOS

- **scenario_engine.py**
  - Escenarios fijos: raise, hold, lower.
  - _get_scenario_context(briefing): alert_types, has_critical/high_alerts, signal_types, demand_score, demand_signal, strategy_label, consolidated_price_action, action_types.
  - _score_raise, _score_hold, _score_lower: devuelven (support_score, risk_score) en escala 0–5. Heurísticas: demand strong/underpriced/premium apoyan raise; parity/weak demand/defensive/overpriced penalizan raise. Hold apoyado por defensive, parity, weak demand, market compression. Lower apoyado por overpriced, weak demand, demand collapse; penalizado por strong demand, premium.
  - net_score = support_score - risk_score; verdict: strong (net >= 2), medium (net >= 0), weak (net < 0).
  - _reason_raise, _reason_hold, _reason_lower: razones legibles por escenario.
  - _recommended_scenario(assessment): mayor net_score; empate preferir hold > raise > lower.
  - _build_scenario_summary, _build_scenario_risks, _build_scenario_tradeoffs.
  - build_scenario_assessment(briefing) devuelve: scenario_assessment, scenario_summary, recommended_scenario, scenario_risks, scenario_tradeoffs.

- **orchestrator.py**
  - Import build_scenario_assessment. Tras Value Prioritization: scenario_results = build_scenario_assessment(briefing); briefing.update(scenario_results). En run_full_analysis y run_fast_demo.

- **agents/agent_07_report.py**
  - Lectura de scenario_assessment, scenario_summary, recommended_scenario, scenario_risks, scenario_tradeoffs.
  - Nuevo bloque en el prompt: "ESCENARIOS EVALUADOS POR REVMAX" con recommended_scenario, scenario_summary, scenario_assessment (support, risk, net, verdict, reason), scenario_risks, scenario_tradeoffs.
  - Regla ESCENARIOS: usar solo los tres escenarios (raise, hold, lower); explicar por qué el recomendado es más defendible; usar scenario_summary en parte ejecutiva; no inventar escenarios; citar support/risk solo si ayuda.

- **tests/test_scenario_engine.py**
  - demand strong + underpriced => raise recomendado; parity violation + weak demand => hold recomendado; weak demand + overpriced => lower o hold; defensive penaliza raise; premium apoya raise; scenario_assessment contiene raise/hold/lower; net_score = support - risk; recommended_scenario existe.

---

## 4. CÓDIGO COMPLETO

### scenario_engine.py

Ver archivo `scenario_engine.py` en el repositorio. Contiene: SCENARIOS, VERDICT_*, SCORE_CAP; _get_scenario_context; _score_raise, _score_hold, _score_lower; _verdict_from_net; _reason_raise, _reason_hold, _reason_lower; _build_assessment; _recommended_scenario; _build_scenario_summary, _build_scenario_risks, _build_scenario_tradeoffs; build_scenario_assessment(briefing).

### orchestrator.py (fragmentos)

- Import: `from scenario_engine import build_scenario_assessment`
- Tras `briefing.update(value_results)`: `scenario_results = build_scenario_assessment(briefing)`; `briefing.update(scenario_results)` en ambos flujos.

### agent_07_report.py (fragmentos)

- Variables: scenario_assessment, scenario_summary, recommended_scenario, scenario_risks, scenario_tradeoffs.
- Bloque "ESCENARIOS EVALUADOS POR REVMAX" con recommended_scenario, scenario_summary, lista scenario_assessment (support, risk, net, verdict, reason), scenario_risks, scenario_tradeoffs.
- Regla: "ESCENARIOS: Usa SOLO los tres escenarios evaluados por código (raise, hold, lower). El informe debe poder explicar por qué el escenario recomendado parece más defendible. Usa scenario_summary en la parte ejecutiva. No inventes escenarios. Cita support_score o risk_score solo si ayuda."

### tests/test_scenario_engine.py

Ocho tests según lista del apartado 3.

---

## 5. EJEMPLOS DE ESCENARIOS

| Contexto | raise (support/risk/net) | hold | lower | recommended |
|----------|---------------------------|------|-------|-------------|
| Demand high, underpriced, premium | Alto support, bajo risk | — | — | raise |
| Parity violation, weak demand | Alto risk | Alto support | — | hold |
| Weak demand, overpriced | — | Medio | Alto support | lower o hold |
| Defensive, medium demand | risk +1.2 por defensive | support +1.5 | — | hold |
| Premium, high demand, underpriced | support +premium +demand +underpriced | — | — | raise |

Ejemplo de scenario_assessment:

```json
{
  "scenario": "hold",
  "support_score": 4.2,
  "risk_score": 1.4,
  "net_score": 2.8,
  "verdict": "strong",
  "reason": "Hold aligns with defensive posture and current alert profile."
}
```

---

## 6. LÍMITES DEL SISTEMA

- No hay simulación monetaria ni elasticidades ni optimización de revenue ni ML.
- Scoring es heurístico (reglas fijas); no se calibra con datos históricos.
- Solo tres escenarios (raise, hold, lower); no escenarios compuestos ni horizontes múltiples.
- No sustituye la consolidación; la decisión consolidada sigue viniendo de consolidate(); el engine solo añade comparación explícita.
- scenario_risks y scenario_tradeoffs son listas de texto; no estructuras tipadas para dashboard ni persistencia específica.
