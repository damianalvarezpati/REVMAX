# Fase 3 — Entrega: Strategy Engine

---

## DEBILIDADES QUE RESUELVE ESTA FASE

1. **Falta de postura estratégica**: El sistema analizaba señales y consolidaba una decisión de precio sin una etiqueta de estrategia (AGGRESSIVE, BALANCED, PREMIUM, DEFENSIVE). No quedaba explícito si el hotel debía priorizar ocupación, ADR o protección.

2. **Decisión sin contexto estratégico**: La consolidación no modulaba la decisión según la postura. Una misma señal (p. ej. pricing recomienda raise) podía tratarse igual en un contexto de captación que en uno premium.

3. **Informe sin marco estratégico**: El report no nombraba ninguna estrategia ni explicaba por qué RevMax interpretaba una postura; las priority_actions no se conectaban con un marco estratégico.

4. **Sin trazabilidad de la estrategia**: No existían strategy_drivers, strategy_risks ni strategy_influence_on_decision, por lo que no se podía auditar por qué se había elegido una postura ni cómo había influido en la decisión final.

---

## ARCHIVOS MODIFICADOS

- **orchestrator.py** — Import del strategy_engine; en `consolidate()`: derivación de estrategia, modulación de señales y campos de estrategia en el briefing; línea de log con estrategia.
- **agents/agent_07_report.py** — Lectura de strategy_* y strategy_influence_on_decision del briefing; sección "ESTRATEGIA DERIVADA" en el prompt; regla para nombrar la estrategia y conectarla con las priority_actions.
- **strategy_engine.py** — Nuevo: derivación de estrategia, modulación de señales y texto de influencia.
- **tests/test_strategy.py** — Nuevo: tests de derivación (PREMIUM, BALANCED, DEFENSIVE, AGGRESSIVE) y de que la estrategia afecta el briefing y la modulación.

---

## CAMBIOS IMPLEMENTADOS

### Cómo se deriva la estrategia

- **strategy_engine.derive_strategy(agent_outputs, conflicts)** usa solo señales ya presentes en el pipeline: pricing (acción, ranking), demand (signal), reputation (GRI, can_command_premium), distribution (paridad, visibilidad), y conflictos (severidad high).
- **Orden de evaluación**: DEFENSIVE > AGGRESSIVE > PREMIUM > BALANCED.
- **DEFENSIVE**: si hay violación de paridad o algún conflicto de severidad high (p. ej. pricing raise + demand low).
- **AGGRESSIVE**: si demanda baja y (visibilidad &lt; 0.5 o posición débil rank/total &gt; 0.5), o si demanda baja y pricing recomienda lower.
- **PREMIUM**: si GRI ≥ 78, can_premium, demanda no baja, sin paridad violada, y (pricing raise o posición fuerte rank/total ≤ 0.4).
- **BALANCED**: en el resto de casos (señales neutras o mixtas).

### Reglas o pesos

- **STRATEGY_CONFIG** en strategy_engine.py: gri_min_premium (78), weak_position_ratio (0.5), strong_position_ratio (0.4), visibility_low_threshold (0.5), defensive_hold_boost (0.35), defensive_raise_mult (0.5), aggressive_raise_mult (0.75), aggressive_hold_boost (0.2), premium_raise_boost (0.25). La modulación usa estos valores; la derivación usa los umbrales.

### Cómo influye en consolidate()

- Tras aplicar conflict_penalties se obtiene **demand_signal** y se llama a **derive_strategy(agent_outputs, conflicts)**.
- Se calcula **action_before_strategy** con las señales actuales.
- Se llama a **apply_strategy_modulation(signals, strategy_label, demand_signal=..., p_action=...)** que modifica el dict de señales in-place: DEFENSIVE refuerza hold y reduce raise; AGGRESSIVE (con demanda baja) reduce raise y refuerza hold; PREMIUM (con p_action raise) refuerza raise; BALANCED no cambia nada.
- La **final_action** se obtiene después de la modulación con _final_action_from_signals(signals).
- **strategy_influence_on_decision** se construye comparando action_before_strategy y final_action.

### Nuevos campos en el briefing

- strategy_label, strategy_rationale, strategy_drivers, strategy_risks, strategy_confidence, strategy_influence_on_decision. Todos llegan al report agent en el prompt.

### Cómo se refleja en el report

- El prompt incluye la sección "ESTRATEGIA DERIVADA" con los campos anteriores.
- Una regla obligatoria indica que el informe debe nombrar la estrategia (strategy_label), explicar en 1–2 frases por qué RevMax interpreta esa postura (usando strategy_rationale y strategy_drivers) y conectar esa estrategia con las priority_actions, sin sonar artificial.

### Tests añadidos

- **test_strategy_premium_strong_reputation_and_pricing**: GRI alto, can_premium, demanda media, pricing raise, posición fuerte → PREMIUM.
- **test_strategy_balanced_neutral_signals**: señales neutras → BALANCED.
- **test_strategy_defensive_parity_violation**: paridad violation → DEFENSIVE.
- **test_strategy_defensive_high_conflict**: pricing raise + demand low → DEFENSIVE.
- **test_strategy_aggressive_low_demand_weak_position**: demanda baja y rank/total &gt; 0.5 → AGGRESSIVE.
- **test_strategy_aggressive_low_demand_low_visibility**: demanda baja y visibilidad &lt; 0.5 → AGGRESSIVE.
- **test_strategy_affects_consolidation_briefing**: el briefing contiene strategy_label, strategy_rationale, strategy_drivers, strategy_risks, strategy_confidence, strategy_influence_on_decision.
- **test_strategy_modulation_defensive_reduces_raise** y **test_strategy_modulation_premium_boosts_raise**: la modulación cambia las señales como se espera.
- **test_strategy_config_defined**: STRATEGY_CONFIG tiene las claves esperadas.

---

## CÓDIGO COMPLETO

### strategy_engine.py

```python
"""
RevMax — Strategy Engine (Fase 3)
==================================
Deriva la postura estratégica del hotel a partir de señales existentes
y modula la decisión consolidada. Solo reglas explícitas y umbrales centralizados.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Umbrales y factores para derivación y modulación de estrategia.
# ─────────────────────────────────────────────────────────────────────────────
STRATEGY_CONFIG = {
    "gri_min_premium": 78,
    "weak_position_ratio": 0.5,
    "strong_position_ratio": 0.4,
    "visibility_low_threshold": 0.5,
    "defensive_hold_boost": 0.35,
    "defensive_raise_mult": 0.5,
    "aggressive_raise_mult": 0.75,
    "aggressive_hold_boost": 0.2,
    "premium_raise_boost": 0.25,
}

STRATEGY_LABELS = ("DEFENSIVE", "AGGRESSIVE", "PREMIUM", "BALANCED")


def derive_strategy(agent_outputs: dict, conflicts: list) -> dict:
    """
    Deriva la estrategia del hotel a partir de señales actuales.
    Orden de evaluación: DEFENSIVE > AGGRESSIVE > PREMIUM > BALANCED.
    Devuelve: strategy_label, strategy_rationale, strategy_drivers, strategy_risks, strategy_confidence.
    """
    pricing = agent_outputs.get("pricing", {})
    demand = agent_outputs.get("demand", {})
    reputation = agent_outputs.get("reputation", {})
    distribution = agent_outputs.get("distribution", {})

    p_action = pricing.get("recommendation", {}).get("action", "hold")
    demand_signal = demand.get("demand_index", {}).get("signal", "medium")
    gri_val = reputation.get("gri", {}).get("value") or 0
    can_premium = reputation.get("gri", {}).get("can_command_premium", False)
    your_rank = pricing.get("market_context", {}).get("your_position_rank", 5)
    total = pricing.get("market_context", {}).get("total_compset", 10) or 10
    visibility = distribution.get("visibility_score", 1.0) or 1.0
    parity_status = distribution.get("rate_parity", {}).get("status", "ok")

    has_high_conflict = any(c.get("severity") == "high" for c in conflicts)
    parity_violation = parity_status == "violation"
    rank_ratio = (your_rank / total) if total else 0.5
    weak_position = rank_ratio > STRATEGY_CONFIG["weak_position_ratio"]
    strong_position = rank_ratio <= STRATEGY_CONFIG["strong_position_ratio"]
    visibility_low = isinstance(visibility, (int, float)) and visibility < STRATEGY_CONFIG["visibility_low_threshold"]
    demand_low = demand_signal in ("low", "very_low")
    gri_ok = isinstance(gri_val, (int, float)) and gri_val >= STRATEGY_CONFIG["gri_min_premium"]

    # 1. DEFENSIVE: paridad, conflictos altos o entorno de alerta
    if parity_violation or has_high_conflict:
        drivers = []
        if parity_violation:
            drivers.append("Violación de paridad de tarifas.")
        if has_high_conflict:
            drivers.append("Conflictos de alta severidad entre señales.")
        return {
            "strategy_label": "DEFENSIVE",
            "strategy_rationale": "Proteger la posición ante señales negativas o incertidumbre. Evitar movimientos arriesgados hasta resolver conflictos.",
            "strategy_drivers": drivers,
            "strategy_risks": ["Entorno incierto o hostil; priorizar protección de posición y consistencia."],
            "strategy_confidence": 0.9,
        }

    # 2. AGGRESSIVE: captación / ocupación / llenado
    if demand_low and (visibility_low or weak_position):
        drivers = ["Demanda baja; prioridad a ocupación y llenado."]
        if visibility_low:
            drivers.append("Visibilidad baja; necesidad de captar reservas.")
        if weak_position:
            drivers.append("Posición débil en compset; presión competitiva.")
        return {
            "strategy_label": "AGGRESSIVE",
            "strategy_rationale": "Foco en captación y ocupación. La demanda y/o posición no justifican subir precio; priorizar volumen.",
            "strategy_drivers": drivers,
            "strategy_risks": ["Subir precio ahora puede costar ocupación."],
            "strategy_confidence": 0.75,
        }
    if demand_low and p_action == "lower":
        return {
            "strategy_label": "AGGRESSIVE",
            "strategy_rationale": "Demanda baja y pricing recomienda bajar; postura de captación para llenar.",
            "strategy_drivers": ["Demanda baja.", "Pricing recomienda bajar para estimular demanda."],
            "strategy_risks": ["Mantener ADR bajo hasta que demanda repunte."],
            "strategy_confidence": 0.7,
        }

    # 3. PREMIUM: capturar precio alto / posicionamiento fuerte
    if gri_ok and can_premium and not demand_low and not parity_violation and (p_action == "raise" or strong_position):
        drivers = ["GRI alto y capacidad de comandar premium.", "Demanda suficiente para sostener precio."]
        if strong_position:
            drivers.append("Posición de precio fuerte en el compset.")
        if p_action == "raise":
            drivers.append("Pricing recomienda subir.")
        return {
            "strategy_label": "PREMIUM",
            "strategy_rationale": "Reputación y posición permiten capturar precio alto. Priorizar ADR sin sacrificar ocupación de forma imprudente.",
            "strategy_drivers": drivers,
            "strategy_risks": ["No sobrevalorar si la demanda se enfría."],
            "strategy_confidence": 0.8,
        }

    # 4. BALANCED: neutro
    drivers = ["Señales neutras o mixtas.", "Equilibrio entre ADR y ocupación."]
    if demand_signal == "medium":
        drivers.append("Demanda en rango medio.")
    return {
        "strategy_label": "BALANCED",
        "strategy_rationale": "Postura neutra; equilibrio entre precio y ocupación. Sin señales fuertes hacia una estrategia extrema.",
        "strategy_drivers": drivers,
        "strategy_risks": [],
        "strategy_confidence": 0.7,
    }


def apply_strategy_modulation(
    signals: dict,
    strategy_label: str,
    *,
    demand_signal: str = "medium",
    p_action: str = "hold",
) -> None:
    """
    Modula el dict de señales (raise/hold/lower/promo) según la estrategia.
    Modifica signals in-place. No sustituye la decisión; la inclina.
    """
    if strategy_label == "DEFENSIVE":
        boost = STRATEGY_CONFIG["defensive_hold_boost"]
        mult = STRATEGY_CONFIG["defensive_raise_mult"]
        signals["hold"] += boost
        signals["raise"] *= mult
        if "lower" in signals:
            signals["lower"] *= 0.8
    elif strategy_label == "AGGRESSIVE":
        if demand_signal in ("low", "very_low"):
            mult = STRATEGY_CONFIG["aggressive_raise_mult"]
            boost = STRATEGY_CONFIG["aggressive_hold_boost"]
            signals["raise"] *= mult
            signals["hold"] += boost
    elif strategy_label == "PREMIUM":
        if p_action == "raise":
            boost = STRATEGY_CONFIG["premium_raise_boost"]
            signals["raise"] += boost
    # BALANCED: sin cambios


def build_strategy_influence_on_decision(
    strategy_label: str,
    action_before_modulation: str,
    final_action: str,
) -> str:
    """Texto corto que explica cómo la estrategia influyó en la decisión final."""
    if action_before_modulation == final_action:
        return f"Estrategia {strategy_label}: no cambió la decisión ({final_action.upper()})."
    return f"Estrategia {strategy_label} inclinó la decisión de {action_before_modulation.upper()} hacia {final_action.upper()}."
```

### tests/test_strategy.py

```python
"""
Tests unitarios del Strategy Engine (Fase 3).
Ejecutar desde la raíz: pytest tests/test_strategy.py -v
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from strategy_engine import derive_strategy, apply_strategy_modulation, STRATEGY_CONFIG, STRATEGY_LABELS
from orchestrator import detect_conflicts, consolidate


def _base_outputs(
    price_action="hold",
    demand_signal="medium",
    demand_implication="hold",
    gri_value=70,
    can_premium=False,
    parity_status="ok",
    visibility=0.8,
    your_rank=3,
    total=8,
):
    """Outputs mínimos de agentes para montar escenarios."""
    return {
        "pricing": {
            "recommendation": {"action": price_action},
            "market_context": {"your_position_rank": your_rank, "total_compset": total},
            "confidence_score": 0.7,
        },
        "demand": {
            "demand_index": {"signal": demand_signal, "score": 55},
            "price_implication": demand_implication,
            "confidence_score": 0.65,
        },
        "reputation": {
            "gri": {"value": gri_value, "can_command_premium": can_premium, "suggested_premium_pct": 5 if can_premium else 0},
            "confidence_score": 0.75,
        },
        "distribution": {
            "visibility_score": visibility,
            "rate_parity": {"status": parity_status},
            "confidence_score": 0.65,
        },
        "compset": {"confidence_score": 0.7},
    }


def test_strategy_premium_strong_reputation_and_pricing():
    outputs = _base_outputs(price_action="raise", demand_signal="medium", gri_value=82, can_premium=True, parity_status="ok", your_rank=2, total=8)
    conflicts = detect_conflicts(outputs)
    strategy = derive_strategy(outputs, conflicts)
    assert strategy["strategy_label"] == "PREMIUM"
    assert "GRI" in " ".join(strategy["strategy_drivers"]) or "premium" in " ".join(strategy["strategy_drivers"]).lower()
    assert strategy.get("strategy_confidence", 0) >= 0.5


def test_strategy_balanced_neutral_signals():
    outputs = _base_outputs(price_action="hold", demand_signal="medium", gri_value=72, can_premium=False, parity_status="ok")
    conflicts = detect_conflicts(outputs)
    strategy = derive_strategy(outputs, conflicts)
    assert strategy["strategy_label"] == "BALANCED"
    assert "strategy_rationale" in strategy


def test_strategy_defensive_parity_violation():
    outputs = _base_outputs(parity_status="violation")
    conflicts = detect_conflicts(outputs)
    strategy = derive_strategy(outputs, conflicts)
    assert strategy["strategy_label"] == "DEFENSIVE"
    assert any("paridad" in d.lower() or "parity" in d.lower() for d in strategy["strategy_drivers"])


def test_strategy_defensive_high_conflict():
    outputs = _base_outputs(price_action="raise", demand_signal="low", parity_status="ok")
    conflicts = detect_conflicts(outputs)
    strategy = derive_strategy(outputs, conflicts)
    assert strategy["strategy_label"] == "DEFENSIVE"
    assert strategy["strategy_risks"]


def test_strategy_aggressive_low_demand_weak_position():
    outputs = _base_outputs(demand_signal="low", your_rank=6, total=8, parity_status="ok")
    conflicts = detect_conflicts(outputs)
    strategy = derive_strategy(outputs, conflicts)
    assert strategy["strategy_label"] == "AGGRESSIVE"
    assert "Demanda" in " ".join(strategy["strategy_drivers"]) or "ocupación" in strategy["strategy_rationale"].lower() or "captación" in strategy["strategy_rationale"].lower()


def test_strategy_aggressive_low_demand_low_visibility():
    outputs = _base_outputs(demand_signal="low", visibility=0.35, parity_status="ok", your_rank=3, total=8)
    conflicts = detect_conflicts(outputs)
    strategy = derive_strategy(outputs, conflicts)
    assert strategy["strategy_label"] == "AGGRESSIVE"


def test_strategy_affects_consolidation_briefing():
    outputs = _base_outputs(price_action="raise", demand_signal="medium", gri_value=82, can_premium=True)
    conflicts = detect_conflicts(outputs)
    briefing = consolidate(outputs, conflicts)
    assert "strategy_label" in briefing
    assert briefing["strategy_label"] in STRATEGY_LABELS
    assert "strategy_rationale" in briefing
    assert "strategy_drivers" in briefing
    assert "strategy_risks" in briefing
    assert "strategy_confidence" in briefing
    assert "strategy_influence_on_decision" in briefing


def test_strategy_modulation_defensive_reduces_raise():
    signals = {"raise": 1.0, "hold": 0.5, "lower": 0.0, "promo": 0.0}
    apply_strategy_modulation(signals, "DEFENSIVE", demand_signal="medium", p_action="raise")
    assert signals["raise"] < 1.0
    assert signals["hold"] > 0.5


def test_strategy_modulation_premium_boosts_raise():
    signals = {"raise": 0.8, "hold": 0.7, "lower": 0.0, "promo": 0.0}
    apply_strategy_modulation(signals, "PREMIUM", demand_signal="medium", p_action="raise")
    assert signals["raise"] > 0.8


def test_strategy_config_defined():
    c = STRATEGY_CONFIG
    assert "gri_min_premium" in c
    assert "defensive_hold_boost" in c
    assert "premium_raise_boost" in c
    assert "aggressive_raise_mult" in c
```

### orchestrator.py (fragmentos modificados)

- **Imports** (después de run_report_agent):
```python
from strategy_engine import (
    derive_strategy,
    apply_strategy_modulation,
    build_strategy_influence_on_decision,
)
```

- **En consolidate()**, después de `has_high_conflict = _apply_conflict_penalties(signals, conflicts)`:
```python
    demand_signal = demand.get("demand_index", {}).get("signal", "medium")
    strategy = derive_strategy(agent_outputs, conflicts)
    action_before_strategy = _final_action_from_signals(signals)
    apply_strategy_modulation(
        signals,
        strategy["strategy_label"],
        demand_signal=demand_signal,
        p_action=p_action,
    )
    final_action = _final_action_from_signals(signals)
    strategy_influence_on_decision = build_strategy_influence_on_decision(
        strategy["strategy_label"],
        action_before_strategy,
        final_action,
    )
```

- **En el return de consolidate()**, añadir:
```python
        "strategy_label": strategy["strategy_label"],
        "strategy_rationale": strategy["strategy_rationale"],
        "strategy_drivers": strategy["strategy_drivers"],
        "strategy_risks": strategy["strategy_risks"],
        "strategy_confidence": strategy["strategy_confidence"],
        "strategy_influence_on_decision": strategy_influence_on_decision,
```

- **Línea de log** (Fase 4):
```python
    print(f"  Acción: {briefing['consolidated_price_action'].upper()} · Estado: {briefing.get('derived_overall_status', '?')} · Estrategia: {briefing.get('strategy_label', '?')}")
```

### agents/agent_07_report.py (fragmentos modificados)

- **Variables del briefing** (después de action_constraints):
```python
    strategy_label = briefing.get("strategy_label", "")
    strategy_rationale = briefing.get("strategy_rationale", "")
    strategy_drivers = briefing.get("strategy_drivers", [])
    strategy_risks = briefing.get("strategy_risks", [])
    strategy_confidence = briefing.get("strategy_confidence", 0)
    strategy_influence_on_decision = briefing.get("strategy_influence_on_decision", "")
```

- **Sección en el prompt** (después de recommended_priority_actions_seed):
```
ESTRATEGIA DERIVADA (nómbrala en el informe y conecta con las acciones):
  strategy_label: {strategy_label or 'BALANCED'}
  strategy_rationale: ...
  strategy_drivers: ...
  strategy_risks: ...
  strategy_confidence: ...
  strategy_influence_on_decision: ...
```

- **Regla añadida**: ESTRATEGIA: En el informe debes nombrar la estrategia derivada... y conectar con las priority_actions.

(Los archivos completos están en el workspace; los fragmentos anteriores son los cambios relevantes.)

---

## ANTES VS DESPUÉS

### 1. Caso PREMIUM

**Input simplificado:** GRI 82, can_command_premium True, demanda medium, pricing action raise, posición #2 de 8, paridad ok, visibilidad 0.8.

**strategy_label:** PREMIUM  
**strategy_rationale:** Reputación y posición permiten capturar precio alto. Priorizar ADR sin sacrificar ocupación de forma imprudente.  
**Decisión consolidada antes (sin estrategia):** raise (señales base + reputación ya favorecían raise).  
**Decisión consolidada ahora:** raise; la modulación PREMIUM refuerza raise (+0.25), por lo que se mantiene raise.  
**derived_overall_status:** stable  
**Ejemplo de priority_action alineada:** "Subir precio en suite junior según recomendación de Pricing; estrategia PREMIUM respaldada por GRI alto y demanda suficiente."

---

### 2. Caso AGGRESSIVE

**Input simplificado:** Demanda low, visibilidad 0.35, pricing hold, posición #5 de 8, paridad ok.

**strategy_label:** AGGRESSIVE  
**strategy_rationale:** Foco en captación y ocupación. La demanda y/o posición no justifican subir precio; priorizar volumen.  
**Decisión consolidada antes (sin estrategia):** hold (señales neutras).  
**Decisión consolidada ahora:** hold; AGGRESSIVE con demanda baja aplica raise_mult 0.75 y hold_boost 0.2, lo que refuerza hold frente a cualquier raise residual.  
**derived_overall_status:** needs_attention o stable según otros factores.  
**Ejemplo de priority_action alineada:** "Mantener precios y priorizar ocupación; estrategia AGGRESSIVE por demanda baja y visibilidad limitada."

---

### 3. Caso DEFENSIVE

**Input simplificado:** Paridad violation, pricing raise, demanda medium.

**strategy_label:** DEFENSIVE  
**strategy_rationale:** Proteger la posición ante señales negativas o incertidumbre. Evitar movimientos arriesgados hasta resolver conflictos.  
**Decisión consolidada antes (sin estrategia):** ya era hold por parity_hold_boost y parity_raise_lower_mult.  
**Decisión consolidada ahora:** hold; DEFENSIVE añade defensive_hold_boost (0.35) y defensive_raise_mult (0.5), reforzando aún más hold.  
**derived_overall_status:** alert  
**Ejemplo de priority_action alineada:** "Resolver violación de paridad entre canales (urgencia immediate); estrategia DEFENSIVE hasta corregir paridad."

---

## LÍMITES QUE SIGUEN EXISTIENDO

- **Alert engine / scheduler / dashboard:** No implementados; la estrategia no dispara alertas ni se visualiza en ninguna página.
- **Estrategia explícita por hotel:** La estrategia se deriva solo de la corrida actual; no hay configuración guardada ni override por propiedad.
- **Calibración de umbrales:** STRATEGY_CONFIG es fijo; no hay A/B ni calibración por mercado o tipo de hotel.
- **Report agent:** Sigue siendo LLM; puede no nombrar la estrategia o no conectarla bien con las acciones si el prompt no se cumple al 100 %.
- **Más estrategias o sub-etiquetas:** Solo cuatro etiquetas; no hay grados (p. ej. PREMIUM_MODERATE) ni estrategias por canal/room type.
- **Integraciones externas:** No se han añadido nuevas APIs ni fuentes de señal para la estrategia.
