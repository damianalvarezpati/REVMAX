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


def _build_strategy_scorecard(ctx: dict) -> dict:
    """Resumen legible de señales que contribuyen a la estrategia. Valores: high | medium | low | against."""
    rep = "high" if (ctx.get("gri_ok") and ctx.get("can_premium")) else ("low" if not ctx.get("gri_ok") and ctx.get("gri_val", 0) < 60 else "medium")
    demand = "high" if ctx.get("demand_high") else ("low" if ctx.get("demand_low") else "medium")
    pricing = "high" if (ctx.get("p_action") == "raise" and ctx.get("strong_position")) else ("low" if ctx.get("p_action") == "lower" else "medium")
    dist = "against" if ctx.get("parity_violation") else ("low" if ctx.get("visibility_low") else "high")
    conflict = "high" if ctx.get("has_high_conflict") else ("medium" if ctx.get("conflict_count", 0) > 0 else "low")
    return {
        "reputation_support": rep,
        "demand_support": demand,
        "pricing_support": pricing,
        "distribution_support": dist,
        "conflict_pressure": conflict,
    }


def _build_counter_signals(ctx: dict, strategy_label: str) -> list:
    """Señales que van en contra de la estrategia elegida; evita tono dogmático."""
    out = []
    if strategy_label == "DEFENSIVE":
        if ctx.get("demand_high"):
            out.append("Demanda alta podría permitir más margen de maniobra.")
        if ctx.get("gri_ok") and ctx.get("can_premium"):
            out.append("Reputación fuerte podría soportar postura más ambiciosa en otro contexto.")
    elif strategy_label == "AGGRESSIVE":
        if ctx.get("gri_ok") and ctx.get("can_premium"):
            out.append("GRI alto podría soportar una postura premium si la demanda mejorara.")
        if ctx.get("strong_position"):
            out.append("Posición de precio fuerte en compset; en otra demanda podría priorizarse ADR.")
    elif strategy_label == "PREMIUM":
        if ctx.get("demand_signal") == "medium":
            out.append("Demanda no es especialmente alta; limita convicción premium.")
        if ctx.get("visibility_low"):
            out.append("Visibilidad limitada reduce convicción premium.")
        if not ctx.get("strong_position") and ctx.get("p_action") != "raise":
            out.append("Pricing no recomienda subir; refuerza cautela en precio.")
    elif strategy_label == "BALANCED":
        if ctx.get("gri_ok") and ctx.get("demand_high"):
            out.append("Algunas señales apuntarían a PREMIUM.")
        if ctx.get("demand_low") and not ctx.get("has_high_conflict"):
            out.append("Demanda baja podría justificar postura más AGGRESSIVE.")
    return out


def _build_confidence_reason(scorecard: dict, counter_signals: list, strategy_label: str, confidence: float) -> str:
    """Frase que explica por qué la confianza es alta/media/baja."""
    if confidence >= 0.85:
        return "Confianza alta porque las señales clave (reputación, demanda, pricing, distribución, conflictos) apuntan en la misma dirección y hay pocas señales en contra."
    if len(counter_signals) > 0:
        return f"Confianza media porque hay señales a favor de {strategy_label} pero también señales en contra que limitan la convicción."
    sc = scorecard
    aligned = sum(1 for v in sc.values() if v in ("high", "low") and v != "against")
    if aligned >= 4:
        return "Confianza alta porque la mayoría de dimensiones del scorecard apoyan la estrategia y no hay contra-señales relevantes."
    return "Confianza media porque las señales son mixtas; la estrategia es la más coherente con el conjunto pero sin unanimidad."


def derive_strategy(agent_outputs: dict, conflicts: list) -> dict:
    """
    Deriva la estrategia del hotel a partir de señales actuales.
    Orden de evaluación: DEFENSIVE > AGGRESSIVE > PREMIUM > BALANCED.
    Devuelve: strategy_label, strategy_rationale, strategy_drivers, strategy_risks, strategy_confidence,
    strategy_scorecard, strategy_counter_signals, strategy_confidence_reason.
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
    demand_high = demand_signal in ("high", "very_high")
    gri_ok = isinstance(gri_val, (int, float)) and gri_val >= STRATEGY_CONFIG["gri_min_premium"]

    ctx = {
        "p_action": p_action,
        "demand_signal": demand_signal,
        "gri_val": gri_val,
        "can_premium": can_premium,
        "your_rank": your_rank,
        "total": total,
        "visibility": visibility,
        "parity_status": parity_status,
        "has_high_conflict": has_high_conflict,
        "parity_violation": parity_violation,
        "rank_ratio": rank_ratio,
        "weak_position": weak_position,
        "strong_position": strong_position,
        "visibility_low": visibility_low,
        "demand_low": demand_low,
        "demand_high": demand_high,
        "gri_ok": gri_ok,
        "conflict_count": len(conflicts),
    }

    scorecard = _build_strategy_scorecard(ctx)

    # 1. DEFENSIVE: paridad, conflictos altos o entorno de alerta
    if parity_violation or has_high_conflict:
        drivers = []
        if parity_violation:
            drivers.append("Violación de paridad de tarifas.")
        if has_high_conflict:
            drivers.append("Conflictos de alta severidad entre señales.")
        counter = _build_counter_signals(ctx, "DEFENSIVE")
        conf_reason = _build_confidence_reason(scorecard, counter, "DEFENSIVE", 0.9)
        return {
            "strategy_label": "DEFENSIVE",
            "strategy_rationale": "Proteger la posición ante señales negativas o incertidumbre. Evitar movimientos arriesgados hasta resolver conflictos.",
            "strategy_drivers": drivers,
            "strategy_risks": ["Entorno incierto o hostil; priorizar protección de posición y consistencia."],
            "strategy_confidence": 0.9,
            "strategy_scorecard": scorecard,
            "strategy_counter_signals": counter,
            "strategy_confidence_reason": conf_reason,
        }

    # 2. AGGRESSIVE: captación / ocupación / llenado
    if demand_low and (visibility_low or weak_position):
        drivers = ["Demanda baja; prioridad a ocupación y llenado."]
        if visibility_low:
            drivers.append("Visibilidad baja; necesidad de captar reservas.")
        if weak_position:
            drivers.append("Posición débil en compset; presión competitiva.")
        counter = _build_counter_signals(ctx, "AGGRESSIVE")
        conf_reason = _build_confidence_reason(scorecard, counter, "AGGRESSIVE", 0.75)
        return {
            "strategy_label": "AGGRESSIVE",
            "strategy_rationale": "Foco en captación y ocupación. La demanda y/o posición no justifican subir precio; priorizar volumen.",
            "strategy_drivers": drivers,
            "strategy_risks": ["Subir precio ahora puede costar ocupación."],
            "strategy_confidence": 0.75,
            "strategy_scorecard": scorecard,
            "strategy_counter_signals": counter,
            "strategy_confidence_reason": conf_reason,
        }
    if demand_low and p_action == "lower":
        counter = _build_counter_signals(ctx, "AGGRESSIVE")
        conf_reason = _build_confidence_reason(scorecard, counter, "AGGRESSIVE", 0.7)
        return {
            "strategy_label": "AGGRESSIVE",
            "strategy_rationale": "Demanda baja y pricing recomienda bajar; postura de captación para llenar.",
            "strategy_drivers": ["Demanda baja.", "Pricing recomienda bajar para estimular demanda."],
            "strategy_risks": ["Mantener ADR bajo hasta que demanda repunte."],
            "strategy_confidence": 0.7,
            "strategy_scorecard": scorecard,
            "strategy_counter_signals": counter,
            "strategy_confidence_reason": conf_reason,
        }

    # 3. PREMIUM: capturar precio alto / posicionamiento fuerte
    if gri_ok and can_premium and not demand_low and not parity_violation and (p_action == "raise" or strong_position):
        drivers = ["GRI alto y capacidad de comandar premium.", "Demanda suficiente para sostener precio."]
        if strong_position:
            drivers.append("Posición de precio fuerte en el compset.")
        if p_action == "raise":
            drivers.append("Pricing recomienda subir.")
        counter = _build_counter_signals(ctx, "PREMIUM")
        conf_reason = _build_confidence_reason(scorecard, counter, "PREMIUM", 0.8)
        return {
            "strategy_label": "PREMIUM",
            "strategy_rationale": "Reputación y posición permiten capturar precio alto. Priorizar ADR sin sacrificar ocupación de forma imprudente.",
            "strategy_drivers": drivers,
            "strategy_risks": ["No sobrevalorar si la demanda se enfría."],
            "strategy_confidence": 0.8,
            "strategy_scorecard": scorecard,
            "strategy_counter_signals": counter,
            "strategy_confidence_reason": conf_reason,
        }

    # 4. BALANCED: neutro
    drivers = ["Señales neutras o mixtas.", "Equilibrio entre ADR y ocupación."]
    if demand_signal == "medium":
        drivers.append("Demanda en rango medio.")
    counter = _build_counter_signals(ctx, "BALANCED")
    conf_reason = _build_confidence_reason(scorecard, counter, "BALANCED", 0.7)
    return {
        "strategy_label": "BALANCED",
        "strategy_rationale": "Postura neutra; equilibrio entre precio y ocupación. Sin señales fuertes hacia una estrategia extrema.",
        "strategy_drivers": drivers,
        "strategy_risks": [],
        "strategy_confidence": 0.7,
        "strategy_scorecard": scorecard,
        "strategy_counter_signals": counter,
        "strategy_confidence_reason": conf_reason,
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
