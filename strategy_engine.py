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
