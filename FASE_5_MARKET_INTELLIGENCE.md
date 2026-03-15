# Fase 5 — Market Intelligence / Market Signals

---

## 1. PROBLEMA QUE RESUELVE MARKET INTELLIGENCE

Antes de la Fase 5, la consolidación y la estrategia se apoyaban en señales de agentes y conflictos, pero no existía una capa explícita de “señales de mercado” que:

- Clasificara de forma estructurada oportunidades de subida, riesgo de ir caro/barato, presión competitiva y compresión de mercado.
- Asignara a cada señal una intensidad (low, medium, high) y un efecto direccional (raise, hold, lower, caution) para reforzar el “por qué” de la decisión.
- Llegara al briefing y al report para que el informe pudiera citar señales concretas sin inventarlas.

La capa Market Signals genera por código una taxonomía clara y útil que explica y refuerza la consolidación sin sustituirla.

---

## 2. ARCHIVOS MODIFICADOS

- **market_signals.py** (nuevo): módulo con `detect_market_signals(agent_outputs, conflicts, consolidation_result)`, `build_market_signal_summary(signals)`, `count_market_signals_by_effect(signals, effect)`, `MARKET_SIGNAL_CONFIG`, `SIGNAL_STRENGTHS`, `DIRECTIONAL_EFFECTS` y helpers `_safe_int`, `_safe_float`.
- **orchestrator.py**: import de `detect_market_signals`, `build_market_signal_summary`, `count_market_signals_by_effect`; después del Alert Engine en `run_full_analysis` y en `run_fast_demo`: llamada a `detect_market_signals`, asignación en el briefing de `market_signals`, `market_signal_summary`, `market_raise_signal_count`, `market_lower_signal_count`, `market_caution_signal_count`.
- **agents/agent_07_report.py**: lectura de los cinco campos del briefing; bloque "SEÑALES DE MERCADO DETECTADAS POR REVMAX" en el prompt con lista formateada; regla SEÑALES DE MERCADO para usar las señales en el “por qué”, conectar raise con estrategia/acciones y reflejar cautela/lower sin inventar señales.
- **tests/test_market_signals.py** (nuevo): tests para DEMAND_SUPPORTS_INCREASE, WEAK_DEMAND_REQUIRES_CAUTION, UNDERPRICED_RELATIVE_TO_POSITION, OVERPRICED_FOR_CURRENT_DEMAND, MARKET_COMPRESSION (dos variantes), COMPETITOR_PRICE_PRESSURE (upward y downward), estructura de señal, summary/counts y MARKET_SIGNAL_CONFIG.

---

## 3. CAMBIOS IMPLEMENTADOS

- **Tipos de señal:** DEMAND_SUPPORTS_INCREASE (raise), WEAK_DEMAND_REQUIRES_CAUTION (caution), UNDERPRICED_RELATIVE_TO_POSITION (raise), OVERPRICED_FOR_CURRENT_DEMAND (lower), MARKET_COMPRESSION (hold o caution), COMPETITOR_PRICE_PRESSURE (raise o lower). Cada una con type, strength (low|medium|high), message, source, directional_effect (raise|hold|lower|caution).
- **MARKET_SIGNAL_CONFIG:** demand_high_score_min 65, demand_low_score_max 45, demand_very_high_score_min 75, gri_undervalue_min 78, rank_ratio_weak_position 0.5, rank_ratio_strong_position 0.35, compression_conflict_count_min 2.
- **Orchestrator:** Tras el bloque del Alert Engine se llama `detect_market_signals(outputs, conflicts, briefing)` y se actualiza el briefing con los cinco campos.
- **Report:** El prompt incluye la sección de señales de mercado con summary, counts y lista; la regla obliga a usar las señales para reforzar el “por qué”, conectar raise con estrategia/acciones y reflejar caution/lower sin inventar.

---

## 4. CÓDIGO COMPLETO

### market_signals.py

El archivo completo está en el workspace: desde la cabecera del módulo hasta `count_market_signals_by_effect`. Incluye SIGNAL_STRENGTHS, DIRECTIONAL_EFFECTS, MARKET_SIGNAL_CONFIG, _safe_int, _safe_float, detect_market_signals (con las seis familias de señales), build_market_signal_summary y count_market_signals_by_effect.

### Cambios en orchestrator.py

**Import (junto a alerts_engine):**
```python
from market_signals import (
    detect_market_signals,
    build_market_signal_summary,
    count_market_signals_by_effect,
)
```

**Tras el bloque del Alert Engine en run_full_analysis:**
```python
    market_signals = detect_market_signals(outputs, conflicts, briefing)
    briefing["market_signals"] = market_signals
    briefing["market_signal_summary"] = build_market_signal_summary(market_signals)
    briefing["market_raise_signal_count"] = count_market_signals_by_effect(market_signals, "raise")
    briefing["market_lower_signal_count"] = count_market_signals_by_effect(market_signals, "lower")
    briefing["market_caution_signal_count"] = count_market_signals_by_effect(market_signals, "caution")
```

**Lo mismo tras el bloque del Alert Engine en run_fast_demo:** las mismas cinco líneas que actualizan el briefing con market_signals y los cuatro campos derivados.

### Cambios en agents/agent_07_report.py

**Variables del briefing (después de alert_critical_count):**
```python
    market_signals = briefing.get("market_signals", [])
    market_signal_summary = briefing.get("market_signal_summary", "")
    market_raise_signal_count = briefing.get("market_raise_signal_count", 0)
    market_lower_signal_count = briefing.get("market_lower_signal_count", 0)
    market_caution_signal_count = briefing.get("market_caution_signal_count", 0)
```

**Bloque nuevo en el prompt (después de ALERTAS DETECTADAS POR REVMAX):**
```
SEÑALES DE MERCADO DETECTADAS POR REVMAX (usan para reforzar el "por qué"; no inventar señales fuera de esta lista):
  market_signal_summary: ...
  market_raise_signal_count: ...
  market_lower_signal_count: ...
  market_caution_signal_count: ...
  Lista de señales:
  [strength] type → directional_effect (source): message
```

**Regla nueva antes de "Genera el informe siguiendo EXACTAMENTE...":**
```
- SEÑALES DE MERCADO: Usa las market_signals para reforzar el "por qué" de la decisión consolidada. Si hay señales raise fuertes (market_raise_signal_count: X), conéctalas con la estrategia y las acciones en report_text. Si hay señales caution o lower (market_caution_signal_count, market_lower_signal_count), refleja prudencia en el tono. No inventes señales que no estén en la lista detectada por código.
```

### tests/test_market_signals.py

El archivo completo está en el workspace: 11 tests (demand supports increase, weak demand caution, underpriced relative to position, overpriced for current demand, market compression x2, competitor pressure upward/downward, signal structure, summary and counts, config defined).

---

## 5. EJEMPLOS REALES DE MARKET SIGNALS

- **DEMAND_SUPPORTS_INCREASE:** demand_signal high, demand_score 72 → type DEMAND_SUPPORTS_INCREASE, strength medium, message "Demand conditions support a price increase.", source demand, directional_effect raise.

- **WEAK_DEMAND_REQUIRES_CAUTION:** demand_signal low, demand_score 38 → type WEAK_DEMAND_REQUIRES_CAUTION, strength high, message "Weak demand does not support aggressive price actions; favour hold or lower.", source demand, directional_effect caution.

- **UNDERPRICED_RELATIVE_TO_POSITION:** GRI 84, can_premium True, rank 6/8 → type UNDERPRICED_RELATIVE_TO_POSITION, strength medium, message "Reputation and position allow capturing more price than currently achieved.", source reputation, directional_effect raise.

- **OVERPRICED_FOR_CURRENT_DEMAND:** p_action raise, demand_signal low → type OVERPRICED_FOR_CURRENT_DEMAND, strength high, message "Pricing suggests raise but demand is low; current posture may be too high for market.", source pricing, directional_effect lower.

- **MARKET_COMPRESSION:** demand high y 3 conflictos → type MARKET_COMPRESSION, strength high, message "Tight market: high demand and conflicting signals suggest compressed availability and competition.", source pricing, directional_effect hold. Alternativa: demand high y visibility &lt; 0.5 → strength medium, directional_effect caution.

- **COMPETITOR_PRICE_PRESSURE (upward):** rank 7/8, total 8 → type COMPETITOR_PRICE_PRESSURE, strength high, message "Hotel is behind compset on price; upward pressure to align or capture share.", source pricing, directional_effect raise.

- **COMPETITOR_PRICE_PRESSURE (downward):** rank 1/8, demand low → type COMPETITOR_PRICE_PRESSURE, strength medium, message "Hotel is ahead of compset but demand is weak; downward pressure from market.", source pricing, directional_effect lower.

---

## 6. LÍMITES DEL SISTEMA

- Las señales dependen de la estructura actual de agent_outputs y de consolidation_result; cambios de formato en agentes o consolidación pueden requerir ajustes en detect_market_signals.
- No hay persistencia ni histórico de señales; cada ejecución genera la lista desde cero.
- Los umbrales en MARKET_SIGNAL_CONFIG son fijos; no hay calibración por mercado ni por tipo de hotel.
- El report agent sigue siendo LLM; puede no citar o conectar bien las señales si no sigue el prompt.
- No se han añadido notificaciones automáticas, histórico, nuevas páginas del dashboard, scheduler, machine learning ni nuevas integraciones externas; no se ha tocado el Job Engine.
