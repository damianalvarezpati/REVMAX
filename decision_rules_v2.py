"""
RevMax — Núcleo determinista v2 (primer corte)
================================================
Motor simple, rápido y totalmente auditable.

Características:
- Usa el mapeo v1 (build_signals_from_pipeline) y normalización base.
- Deriva indicadores por buckets y calcula scores de raise/lower.
- Aplica restricciones duras antes de decidir.
- Devuelve:
  - decision: raise|hold|lower
  - confidence: 0..100
  - suggested_action: texto + rangos + guardrails + review_in_hours
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from decision_rules import build_signals_from_pipeline, normalize_signals as normalize_signals_v1


def _clamp_0_100(x: float) -> int:
    return int(max(0, min(100, round(x))))


def _bucket_price_posture(rel_price_diff: Optional[float]) -> Optional[str]:
    """
    price_posture: very_low / low / aligned / high / very_high
    """
    if rel_price_diff is None:
        return None
    if rel_price_diff <= -0.15:
        return "very_low"
    if rel_price_diff <= -0.05:
        return "low"
    if rel_price_diff < 0.05 and rel_price_diff > -0.05:
        return "aligned"
    if rel_price_diff < 0.15:
        return "high"
    return "very_high"


def _bucket_demand_bucket(demand_score: Optional[float]) -> Optional[str]:
    """
    demand_bucket: very_low / low / medium / high / very_high
    """
    if demand_score is None:
        return None
    if demand_score <= 35:
        return "very_low"
    if demand_score <= 50:
        return "low"
    if demand_score < 70:
        return "medium"
    if demand_score < 85:
        return "high"
    return "very_high"


def _bucket_reputation_bucket(gri: Optional[float]) -> Optional[str]:
    """
    reputation_bucket: strong / good / weak / poor
    """
    if gri is None:
        return None
    if gri >= 80:
        return "strong"
    if gri >= 65:
        return "good"
    if gri >= 45:
        return "weak"
    return "poor"


def _bucket_visibility_bucket(v: Optional[float]) -> Optional[str]:
    """
    visibility_bucket: low / medium / good
    """
    if v is None:
        return None
    if v < 0.33:
        return "low"
    if v < 0.66:
        return "medium"
    return "good"


def _market_heat(visibility_bucket: Optional[str], demand_bucket: Optional[str]) -> Optional[float]:
    if visibility_bucket is None or demand_bucket is None:
        return None

    demand_strength = {
        "very_low": 0.0,
        "low": 0.25,
        "medium": 0.5,
        "high": 0.75,
        "very_high": 1.0,
    }.get(demand_bucket, 0.5)

    visibility_strength = {
        "low": 0.25,
        "medium": 0.6,
        "good": 1.0,
    }.get(visibility_bucket, 0.5)

    # heat: promedio determinista
    return round(0.5 * demand_strength + 0.5 * visibility_strength, 3)


def normalize_signals(signals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extiende la normalize_signals v1 con buckets y campos derivados.
    """
    n = normalize_signals_v1(signals)

    rel_price_diff = n.get("price_rel_diff")
    price_posture_v2 = _bucket_price_posture(rel_price_diff)
    demand_bucket = _bucket_demand_bucket(n.get("demand_score"))
    reputation_bucket = _bucket_reputation_bucket(n.get("reputation_gri"))
    visibility_bucket = _bucket_visibility_bucket(n.get("visibility_score"))

    n.update(
        {
            "rel_price_diff": rel_price_diff,
            "price_posture": price_posture_v2,
            "demand_bucket": demand_bucket,
            "reputation_bucket": reputation_bucket,
            "visibility_bucket": visibility_bucket,
            "market_heat": _market_heat(visibility_bucket, demand_bucket),
        }
    )
    return n


def compute_raise_score(normalized: Dict[str, Any]) -> int:
    """
    Score determinista para raise (0..100).
    """
    price_posture = normalized.get("price_posture")
    demand_bucket = normalized.get("demand_bucket")
    reputation_bucket = normalized.get("reputation_bucket")
    visibility_bucket = normalized.get("visibility_bucket")
    events_present = bool(normalized.get("events_present"))
    events_count = int(normalized.get("events_count") or 0)
    market_heat = normalized.get("market_heat")
    parity_status = normalized.get("parity_status")

    score = 50

    score += {
        "very_low": 30,
        "low": 20,
        "aligned": 5,
        "high": -15,
        "very_high": -25,
        None: 0,
    }.get(price_posture, 0)

    score += {
        "very_high": 25,
        "high": 15,
        "medium": 5,
        "low": -10,
        "very_low": -20,
        None: 0,
    }.get(demand_bucket, 0)

    score += {
        "strong": 8,
        "good": 4,
        "weak": -2,
        "poor": -8,
        None: 0,
    }.get(reputation_bucket, 0)

    score += {
        "good": 8,
        "medium": 3,
        "low": -10,
        None: 0,
    }.get(visibility_bucket, 0)

    if events_present:
        score += 5 if events_count >= 2 else 3

    if parity_status == "warning":
        score -= 3

    if market_heat is not None:
        # heat 0..1 => -5..+5 aprox
        score += (market_heat - 0.5) * 10

    return _clamp_0_100(score)


def compute_lower_score(normalized: Dict[str, Any]) -> int:
    """
    Score determinista para lower (0..100).
    """
    price_posture = normalized.get("price_posture")
    demand_bucket = normalized.get("demand_bucket")
    reputation_bucket = normalized.get("reputation_bucket")
    visibility_bucket = normalized.get("visibility_bucket")
    events_present = bool(normalized.get("events_present"))
    events_count = int(normalized.get("events_count") or 0)
    market_heat = normalized.get("market_heat")
    parity_status = normalized.get("parity_status")

    score = 50

    score += {
        "very_high": 30,
        "high": 20,
        "aligned": 5,
        "low": -15,
        "very_low": -25,
        None: 0,
    }.get(price_posture, 0)

    score += {
        "very_low": 25,
        "low": 15,
        "medium": 5,
        "high": -10,
        "very_high": -20,
        None: 0,
    }.get(demand_bucket, 0)

    score += {
        "poor": 8,
        "weak": 4,
        "good": -3,
        "strong": -8,
        None: 0,
    }.get(reputation_bucket, 0)

    score += {
        "low": 8,
        "medium": 3,
        "good": -5,
        None: 0,
    }.get(visibility_bucket, 0)

    if events_present:
        # si hay eventos, normalmente mejora demanda => reduce necesidad de lower
        score -= 3 if events_count >= 2 else 2

    if parity_status == "warning":
        score -= 3

    if market_heat is not None:
        # heat alto favorece raise (y limita lower)
        score += (0.5 - market_heat) * 10

    return _clamp_0_100(score)


def _data_quality_summary(normalized: Dict[str, Any]) -> Dict[str, Any]:
    critical = ["own_price", "compset_avg", "demand_score", "visibility_score", "parity_status"]
    missing = [k for k in critical if normalized.get(k) is None]
    present = [k for k in critical if normalized.get(k) is not None]
    return {
        "critical_missing": missing,
        "critical_present": present,
        "critical_present_count": len(present),
    }


def decide(normalized: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decision final basada en raise_score/lower_score y restricciones duras.
    """
    parity_status = normalized.get("parity_status")
    visibility_bucket = normalized.get("visibility_bucket")
    price_posture = normalized.get("price_posture")

    constraints: List[str] = []

    # Restricciones duras
    if parity_status == "violation":
        constraints.append("parity_violation")
        return {
            "decision": "hold",
            "confidence": 25,
            "raise_score": 0,
            "lower_score": 0,
            "gap": 0,
            "suggested_action": {
                "primary": "Hold y prioriza FIX_PARITY / corrección de paridad.",
                "review_in_hours": 24,
                "guardrails": ["parity_status=violation"],
            },
            "constraints_applied": constraints,
            "data_quality": _data_quality_summary(normalized),
        }

    missing_critical = _data_quality_summary(normalized).get("critical_missing") or []
    if missing_critical:
        constraints.append("missing_critical_data")
        return {
            "decision": "hold",
            "confidence": 20,
            "raise_score": 0,
            "lower_score": 0,
            "gap": 0,
            "suggested_action": {
                "primary": "Hold temporal: faltan datos críticos para decidir.",
                "review_in_hours": 48,
                "guardrails": [f"missing={', '.join(missing_critical[:4])}"],
            },
            "constraints_applied": constraints,
            "data_quality": _data_quality_summary(normalized),
        }

    # visibilidad baja + precio ya bajo => hold
    if visibility_bucket == "low" and price_posture in ("very_low", "low"):
        constraints.append("visibility_low_plus_price_low")
        return {
            "decision": "hold",
            "confidence": 28,
            "raise_score": 0,
            "lower_score": 0,
            "gap": 0,
            "suggested_action": {
                "primary": "Hold: subir precio sin mejorar visibilidad suele fallar.",
                "review_in_hours": 72,
                "guardrails": ["visibility_bucket=low", "price_posture=low/very_low"],
            },
            "constraints_applied": constraints,
            "data_quality": _data_quality_summary(normalized),
        }

    # Scores (0..100)
    raise_score = compute_raise_score(normalized)
    lower_score = compute_lower_score(normalized)
    gap = raise_score - lower_score

    # Decision final por gap
    if gap >= 12 and raise_score >= 65:
        decision = "raise"
    elif gap <= -12 and lower_score >= 65:
        decision = "lower"
    else:
        decision = "hold"

    # Confidence v2
    dq = _data_quality_summary(normalized)
    quality_factor = 0.0
    if dq.get("critical_present_count", 0) >= 5:
        quality_factor = 1.0
    else:
        quality_factor = dq.get("critical_present_count", 0) / 5.0

    score_gap_bonus = min(30, abs(gap) * 0.8)  # 0..~30
    quality_penalty = (1.0 - quality_factor) * 25  # 0..25

    if decision == "raise":
        conf = 55 + score_gap_bonus - quality_penalty
    elif decision == "lower":
        conf = 55 + score_gap_bonus - quality_penalty
    else:
        # hold: depende del gap (si está cerca, la confianza baja)
        conf = 45 - (min(20, abs(gap) * 0.4)) - quality_penalty

    confidence = _clamp_0_100(conf)

    suggested_action = _build_suggested_action_v2(
        normalized=normalized,
        decision=decision,
        confidence=confidence,
        raise_score=raise_score,
        lower_score=lower_score,
        gap=gap,
    )

    return {
        "decision": decision,
        "confidence": confidence,
        "raise_score": raise_score,
        "lower_score": lower_score,
        "gap": gap,
        "suggested_action": suggested_action,
        "constraints_applied": constraints,
        "data_quality": dq,
    }


def _review_hours_from_confidence(confidence: int, decision: str) -> int:
    if decision == "hold":
        if confidence >= 65:
            return 48
        return 72
    if confidence >= 75:
        return 24
    if confidence >= 60:
        return 48
    return 72


def _build_suggested_action_v2(
    normalized: Dict[str, Any],
    decision: str,
    confidence: int,
    raise_score: int,
    lower_score: int,
    gap: int,
) -> Dict[str, Any]:
    price_posture = normalized.get("price_posture")
    demand_bucket = normalized.get("demand_bucket")
    visibility_bucket = normalized.get("visibility_bucket")
    events_present = bool(normalized.get("events_present"))
    events_count = int(normalized.get("events_count") or 0)
    reputation_bucket = normalized.get("reputation_bucket")

    guardrails: List[str] = []
    if normalized.get("parity_status") == "warning":
        guardrails.append("parity_status=warning (vigilancia)")
    if visibility_bucket == "low":
        guardrails.append("visibility_bucket=low")

    review_in_hours = _review_hours_from_confidence(confidence, decision)

    if decision == "raise":
        if price_posture == "very_low":
            rng = "+10% a +15%"
        elif price_posture == "low":
            rng = "+6% a +10%"
        else:
            rng = "+3% a +6%"

        severity = "alta" if demand_bucket in ("high", "very_high") else "media"
        guardrails.append("subir gradualmente; vigilar disponibilidad")
        if not events_present:
            guardrails.append("sin eventos: confirmar demanda en 24-48h")

        return {
            "primary": f"RAISE recomendado ({severity}). Ajuste sugerido: {rng}.",
            "review_in_hours": review_in_hours,
            "guardrails": guardrails,
            "raise_reason_components": {
                "price_posture": price_posture,
                "demand_bucket": demand_bucket,
                "visibility_bucket": visibility_bucket,
                "reputation_bucket": reputation_bucket,
            },
        }

    if decision == "lower":
        if price_posture == "very_high":
            rng = "-10% a -15%"
        elif price_posture == "high":
            rng = "-6% a -10%"
        else:
            rng = "-3% a -6%"

        severity = "alta" if demand_bucket in ("very_low", "low") else "media"
        guardrails.append("bajar gradualmente; evitar pérdida de demanda")
        if events_present:
            guardrails.append(f"hay eventos (count={events_count}); confirmar elasticidad")

        return {
            "primary": f"LOWER recomendado ({severity}). Ajuste sugerido: {rng}.",
            "review_in_hours": review_in_hours,
            "guardrails": guardrails,
            "lower_reason_components": {
                "price_posture": price_posture,
                "demand_bucket": demand_bucket,
                "visibility_bucket": visibility_bucket,
                "reputation_bucket": reputation_bucket,
            },
        }

    # hold
    primary = "Hold: mantener precio y revisar señales (demanda/visibilidad/paridad)."

    return {
        "primary": primary,
        "review_in_hours": review_in_hours,
        "guardrails": guardrails + ["gap entre raise/lower no suficientemente claro"],
    }


def build_deterministic_decision_v2(full_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience: construye señales -> normaliza -> decide v2.
    """
    signals = build_signals_from_pipeline(full_analysis)
    normalized = normalize_signals(signals)
    # Le damos al normalized un hint opcional para review, sin depender de un campo no documentado
    return decide(normalized)

