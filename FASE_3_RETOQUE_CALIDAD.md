# Fase 3 — Retoque de calidad: Strategy Engine más explicable y auditable

---

## 1. DEBILIDADES QUE CORRIGE ESTE RETOQUE

- **Falta de resumen estructurado de señales:** No existía un scorecard que mostrara de un vistazo cómo habían contribuido reputación, demanda, pricing, distribución y conflictos a la estrategia; dificultaba depuración y auditoría.

- **Tono dogmático:** La estrategia se presentaba sin señales en contra; el sistema parecía categórico en lugar de consciente de señales mixtas.

- **Confianza sin explicación:** `strategy_confidence` era solo un número; no había una frase que explicara por qué la confianza era alta o media.

- **Report sin límites:** El informe no tenía instrucción explícita para reconocer counter_signals ni para matizar la convicción con `strategy_confidence_reason`, lo que podía generar un tono excesivamente seguro.

---

## 2. ARCHIVOS MODIFICADOS

- **strategy_engine.py** — Añadidos: `_build_strategy_scorecard(ctx)`, `_build_counter_signals(ctx, strategy_label)`, `_build_confidence_reason(scorecard, counter_signals, strategy_label, confidence)`. Contexto `ctx` compartido; cada rama de `derive_strategy` devuelve `strategy_scorecard`, `strategy_counter_signals`, `strategy_confidence_reason`.

- **orchestrator.py** — El briefing incluye `strategy_scorecard`, `strategy_counter_signals`, `strategy_confidence_reason` (con `.get(..., {})` o `[]`/`""` por defecto).

- **agents/agent_07_report.py** — Variables del briefing: `strategy_scorecard`, `strategy_counter_signals`, `strategy_confidence_reason`. En el prompt: sección ESTRATEGIA DERIVADA ampliada con estos tres campos; regla ESTRATEGIA actualizada para usar `strategy_confidence_reason` y reconocer `strategy_counter_signals` sin sonar categórico.

- **tests/test_strategy.py** — Tests nuevos: `test_strategy_scorecard_exists`, `test_strategy_counter_signals_exists`, `test_strategy_confidence_reason_exists`, `test_premium_with_mixed_signals_produces_counter_signals`, `test_defensive_produces_coherent_confidence_reason`; `test_strategy_affects_consolidation_briefing` ampliado para comprobar los tres campos en el briefing.

---

## 3. CAMBIOS IMPLEMENTADOS

- **strategy_scorecard:** Diccionario con `reputation_support`, `demand_support`, `pricing_support`, `distribution_support`, `conflict_pressure`. Valores: `high` | `medium` | `low` | `against`. Se construye a partir de un contexto `ctx` (gri_ok, can_premium, demand_high/low, p_action, strong_position, parity_violation, visibility_low, has_high_conflict, conflict_count).

- **strategy_counter_signals:** Lista de frases que van en contra de la estrategia elegida. Por estrategia: DEFENSIVE (demanda alta, reputación fuerte); AGGRESSIVE (GRI alto, posición fuerte); PREMIUM (demanda no alta, visibilidad limitada, pricing no raise); BALANCED (señales hacia PREMIUM o AGGRESSIVE).

- **strategy_confidence_reason:** Frase que explica la confianza: si ≥ 0.85 “Confianza alta porque las señales clave apuntan en la misma dirección”; si hay counter_signals “Confianza media porque hay señales a favor pero también en contra”; si no, según alineación del scorecard o “señales mixtas”.

- **orchestrator:** Inclusión de los tres campos en el diccionario devuelto por `consolidate()`.

- **agent_07_report:** Prompt con scorecard (JSON), counter_signals (lista) y confidence_reason; regla para matizar convicción y reconocer límites/contra-señales en una frase.

- **Tests:** Comprobación de existencia y tipo de scorecard/counter_signals/confidence_reason; PREMIUM con demanda medium y visibilidad baja genera counter_signals; DEFENSIVE genera confidence_reason que contiene “confianza”/“alta”/“señales”/“misma”.

---

## 4. CÓDIGO COMPLETO

El código completo está en el workspace en:

- **strategy_engine.py** — Contiene `_build_strategy_scorecard`, `_build_counter_signals`, `_build_confidence_reason` y la integración en cada rama de `derive_strategy` con el contexto `ctx` y los tres nuevos campos en el return.

- **orchestrator.py** — Solo cambia el `return` de `consolidate()` con las tres claves: `strategy_scorecard`, `strategy_counter_signals`, `strategy_confidence_reason`.

- **agents/agent_07_report.py** — Lectura de los tres campos del briefing; en el prompt la sección ESTRATEGIA DERIVADA con `strategy_scorecard`, `strategy_counter_signals`, `strategy_confidence_reason`; regla ESTRATEGIA que pide usar confidence_reason y reconocer counter_signals.

- **tests/test_strategy.py** — Los cinco tests nuevos/ampliados descritos arriba.

---

## 5. DOS EJEMPLOS

### PREMIUM con señales a favor y en contra

**Input:** GRI 82, can_premium True, demanda medium, pricing raise, posición #2/8, paridad ok, visibilidad 0.4.

**strategy_label:** PREMIUM  
**strategy_scorecard:** reputation_support high, demand_support medium, pricing_support high, distribution_support low (visibilidad baja), conflict_pressure low.  
**strategy_counter_signals:** "Demanda no es especialmente alta; limita convicción premium.", "Visibilidad limitada reduce convicción premium."  
**strategy_confidence_reason:** "Confianza media porque hay señales a favor de PREMIUM pero también señales en contra que limitan la convicción."  
**Decisión consolidada:** raise (PREMIUM refuerza raise).  
**Ejemplo para el report:** "RevMax interpreta una postura PREMIUM por GRI y pricing; aunque la demanda no es especialmente alta y la visibilidad es limitada, la primera acción prioritaria refleja subir precio con cautela."

### DEFENSIVE claro

**Input:** Paridad violation, pricing raise, demanda medium.

**strategy_label:** DEFENSIVE  
**strategy_scorecard:** distribution_support against, conflict_pressure high (si hay conflicto) o low, reputation/demand/pricing según datos.  
**strategy_counter_signals:** Posiblemente vacío o “Demanda alta podría permitir más margen” si demanda high.  
**strategy_confidence_reason:** "Confianza alta porque las señales clave (reputación, demanda, pricing, distribución, conflictos) apuntan en la misma dirección y hay pocas señales en contra."  
**Decisión consolidada:** hold.  
**Ejemplo para el report:** "Estrategia DEFENSIVE por violación de paridad; confianza alta. Primera acción: resolver paridad antes de cualquier cambio de precio."

---

## 6. LÍMITES QUE SIGUEN EXISTIENDO

- El scorecard usa categorías fijas (high/medium/low/against) y reglas simples; no hay pesos ni calibración por mercado.
- Los counter_signals son listas fijas por tipo de estrategia; no se generan con lenguaje natural ni se priorizan por impacto.
- La confidence_reason se basa en umbrales (0.85) y en la existencia de counter_signals; no hay modelo de incertidumbre.
- El report agent sigue siendo LLM; puede no citar counter_signals o confidence_reason si no sigue el prompt.
- No hay alert engine, nuevas páginas del dashboard ni cambios en el Job Engine.
