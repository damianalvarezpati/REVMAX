"""
RevMax — Market Intelligence / Market Signals (Fase 5)
======================================================
Detecta señales de mercado útiles y accionables a partir de
agent_outputs, conflicts y consolidation_result.
Generado por código, no por LLM. Refuerza y explica la consolidación.
"""

SIGNAL_STRENGTHS = ("low", "medium", "high")
DIRECTIONAL_EFFECTS = ("raise", "hold", "lower", "caution")

MARKET_SIGNAL_CONFIG = {
    "demand_high_score_min": 65,
    "demand_low_score_max": 45,
    "demand_very_high_score_min": 75,
    "gri_undervalue_min": 78,
    "rank_ratio_weak_position": 0.5,
    "rank_ratio_strong_position": 0.35,
    "compression_conflict_count_min": 2,
    "compression_demand_high": True,
}


def _safe_int(val, default: int = 0) -> int:
    try:
        return int(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def _safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def detect_market_signals(
    agent_outputs: dict,
    conflicts: list,
    consolidation_result: dict,
) -> list[dict]:
    """
    Detecta señales de mercado que explican y refuerzan la consolidación.
    Cada señal: type, strength (low|medium|high), message, source, directional_effect (raise|hold|lower|caution).
    """
    signals = []
    pricing = agent_outputs.get("pricing", {})
    demand = agent_outputs.get("demand", {})
    reputation = agent_outputs.get("reputation", {})
    distribution = agent_outputs.get("distribution", {})

    p_action = pricing.get("recommendation", {}).get("action", "hold")
    demand_signal = demand.get("demand_index", {}).get("signal", "medium")
    demand_score = _safe_int(demand.get("demand_index", {}).get("score"), 50)
    your_rank = pricing.get("market_context", {}).get("your_position_rank")
    total = pricing.get("market_context", {}).get("total_compset", 10) or 10
    visibility = _safe_float(distribution.get("visibility_score"), 1.0)
    gri_val = _safe_int(reputation.get("gri", {}).get("value"), 0)
    can_premium = reputation.get("gri", {}).get("can_command_premium", False)
    consolidated_action = consolidation_result.get("consolidated_price_action", "hold")

    rank_ratio = (your_rank / total) if total and your_rank is not None else 0.5
    demand_high = demand_signal in ("high", "very_high")
    demand_low = demand_signal in ("low", "very_low")

    # DEMAND_SUPPORTS_INCREASE
    if demand_high:
        strength = "high" if demand_score >= MARKET_SIGNAL_CONFIG["demand_very_high_score_min"] else ("medium" if demand_score >= MARKET_SIGNAL_CONFIG["demand_high_score_min"] else "low")
        signals.append({
            "type": "DEMAND_SUPPORTS_INCREASE",
            "strength": strength,
            "message": "Demand conditions support a price increase.",
            "source": "demand",
            "directional_effect": "raise",
        })

    # WEAK_DEMAND_REQUIRES_CAUTION
    if demand_low:
        strength = "high" if demand_score <= MARKET_SIGNAL_CONFIG["demand_low_score_max"] else "medium"
        signals.append({
            "type": "WEAK_DEMAND_REQUIRES_CAUTION",
            "strength": strength,
            "message": "Weak demand does not support aggressive price actions; favour hold or lower.",
            "source": "demand",
            "directional_effect": "caution",
        })

    # UNDERPRICED_RELATIVE_TO_POSITION
    if gri_val >= MARKET_SIGNAL_CONFIG["gri_undervalue_min"] and can_premium and rank_ratio >= MARKET_SIGNAL_CONFIG["rank_ratio_weak_position"]:
        strength = "high" if gri_val >= 85 else "medium"
        signals.append({
            "type": "UNDERPRICED_RELATIVE_TO_POSITION",
            "strength": strength,
            "message": "Reputation and position allow capturing more price than currently achieved.",
            "source": "reputation",
            "directional_effect": "raise",
        })

    # OVERPRICED_FOR_CURRENT_DEMAND
    if p_action == "raise" and demand_low:
        signals.append({
            "type": "OVERPRICED_FOR_CURRENT_DEMAND",
            "strength": "high",
            "message": "Pricing suggests raise but demand is low; current posture may be too high for market.",
            "source": "pricing",
            "directional_effect": "lower",
        })

    # MARKET_COMPRESSION
    if demand_high and len(conflicts) >= MARKET_SIGNAL_CONFIG["compression_conflict_count_min"]:
        strength = "high" if len(conflicts) >= 3 else "medium"
        signals.append({
            "type": "MARKET_COMPRESSION",
            "strength": strength,
            "message": "Tight market: high demand and conflicting signals suggest compressed availability and competition.",
            "source": "pricing",
            "directional_effect": "hold",
        })
    elif demand_high and visibility < 0.5:
        signals.append({
            "type": "MARKET_COMPRESSION",
            "strength": "medium",
            "message": "Strong demand but low visibility; market tension without full capture.",
            "source": "distribution",
            "directional_effect": "caution",
        })

    # COMPETITOR_PRICE_PRESSURE
    if rank_ratio > 0.55 and total >= 5:
        strength = "high" if rank_ratio > 0.7 else "medium"
        signals.append({
            "type": "COMPETITOR_PRICE_PRESSURE",
            "strength": strength,
            "message": "Hotel is behind compset on price; upward pressure to align or capture share.",
            "source": "pricing",
            "directional_effect": "raise",
        })
    elif rank_ratio < MARKET_SIGNAL_CONFIG["rank_ratio_strong_position"] and demand_low:
        signals.append({
            "type": "COMPETITOR_PRICE_PRESSURE",
            "strength": "medium",
            "message": "Hotel is ahead of compset but demand is weak; downward pressure from market.",
            "source": "pricing",
            "directional_effect": "lower",
        })

    return signals


def build_market_signal_summary(signals: list) -> str:
    """Resumen en una frase de las señales de mercado."""
    if not signals:
        return "No hay señales de mercado destacadas."
    raise_n = sum(1 for s in signals if s.get("directional_effect") == "raise")
    lower_n = sum(1 for s in signals if s.get("directional_effect") == "lower")
    caution_n = sum(1 for s in signals if s.get("directional_effect") == "caution")
    hold_n = sum(1 for s in signals if s.get("directional_effect") == "hold")
    parts = []
    if raise_n:
        parts.append(f"{raise_n} señal(es) a favor de subida")
    if lower_n:
        parts.append(f"{lower_n} a favor de bajar")
    if caution_n:
        parts.append(f"{caution_n} de cautela")
    if hold_n:
        parts.append(f"{hold_n} de mantener")
    return "; ".join(parts) + "." if parts else "Señales mixtas."


def count_market_signals_by_effect(signals: list, effect: str) -> int:
    """Cuenta señales con un directional_effect dado."""
    return sum(1 for s in signals if s.get("directional_effect") == effect)
