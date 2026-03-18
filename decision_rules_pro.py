"""
RevMax — Deterministic Decision Engine PRO (sin LLM)
======================================================
Motor auditable y más serio que v1/v2 (todavía simple y rápido):
- Deriva señales `signals` desde el pipeline (mapeo v1).
- Usa buckets de señal (price_posture/demand_bucket/reputation_bucket/visibility_bucket) reutilizando v2.
- Aplica restricciones duras antes de puntuar.
- Calcula raise_score y lower_score deterministas.
- Decide por score gap + umbrales.
- Genera suggested_action con rangos y guardrails.
- Genera reasons y confidence driven by data quality y consistencia.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from decision_rules import build_signals_from_pipeline
from decision_rules_v2 import normalize_signals as normalize_signals_v2


def _event_pressure(events_count: Optional[int]) -> float:
    """
    events_count -> event_pressure (0..1)
    - 0 -> 0.00
    - 1 -> 0.25
    - 2-3 -> 0.60
    - 4+ -> 1.00
    """
    c = int(events_count or 0)
    if c <= 0:
        return 0.0
    if c == 1:
        return 0.25
    if c <= 3:
        return 0.60
    return 1.0


def _clamp_0_100(x: float) -> int:
    return int(max(0, min(100, round(x))))


def _data_quality(normalized: Dict[str, Any]) -> Dict[str, Any]:
    critical = ["own_price", "compset_avg", "demand_score", "visibility_score", "parity_status"]
    present = [k for k in critical if normalized.get(k) is not None]
    missing = [k for k in critical if normalized.get(k) is None]
    # Presentar como "0..1"
    quality_factor = len(present) / len(critical)
    return {
        "critical_present": present,
        "critical_missing": missing,
        "critical_present_count": len(present),
        "quality_factor": round(quality_factor, 3),
    }


def _signal_consistency(normalized: Dict[str, Any], decision: str) -> float:
    """
    Mide consistencia determinista entre señales y la decisión:
    - raise: postura barata + demanda alta + visibilidad ok/good + reputación fuerte + eventos
    - lower: postura cara + demanda baja + visibilidad baja (compensa) + reputación pobre + sin eventos
    Devuelve 0..1
    """
    price_posture = normalized.get("price_posture")
    demand_bucket = normalized.get("demand_bucket")
    reputation_bucket = normalized.get("reputation_bucket")
    visibility_bucket = normalized.get("visibility_bucket")
    event_pressure = normalized.get("event_pressure")

    if decision == "raise":
        checks = [
            price_posture in ("very_low", "low"),
            demand_bucket in ("high", "very_high"),
            reputation_bucket in ("strong", "good"),
            visibility_bucket in ("good", "medium"),
            (event_pressure is not None and event_pressure >= 0.50),
        ]
    elif decision == "lower":
        checks = [
            price_posture in ("very_high", "high"),
            demand_bucket in ("very_low", "low"),
            reputation_bucket in ("poor", "weak"),
            visibility_bucket == "low",
            (event_pressure is not None and event_pressure <= 0.25),
        ]
    else:
        # hold: consistencia relativa al mejor de los dos lados
        raise_checks = [
            price_posture in ("very_low", "low"),
            demand_bucket in ("high", "very_high"),
            reputation_bucket in ("strong", "good"),
            visibility_bucket in ("good", "medium"),
            (event_pressure is not None and event_pressure >= 0.50),
        ]
        lower_checks = [
            price_posture in ("very_high", "high"),
            demand_bucket in ("very_low", "low"),
            reputation_bucket in ("poor", "weak"),
            visibility_bucket == "low",
            (event_pressure is not None and event_pressure <= 0.25),
        ]
        return max(sum(1 for x in raise_checks if x) / 5.0, sum(1 for x in lower_checks if x) / 5.0)

    return sum(1 for x in checks if x) / 5.0


def _compute_raise_score(normalized: Dict[str, Any]) -> int:
    price_posture = normalized.get("price_posture")
    demand_bucket = normalized.get("demand_bucket")
    reputation_bucket = normalized.get("reputation_bucket")
    visibility_bucket = normalized.get("visibility_bucket")
    event_pressure = normalized.get("event_pressure")
    parity_status = normalized.get("parity_status")

    score = 50

    # Precio: si es barato, hay margen para subir
    score += {
        "very_low": 30,
        "low": 20,
        "aligned": 5,
        "high": -10,
        "very_high": -25,
        None: 0,
    }.get(price_posture, 0)

    # Demanda: si demanda alta, sube el incentivo
    score += {
        "very_high": 25,
        "high": 15,
        "medium": 5,
        "low": -10,
        "very_low": -22,
        None: 0,
    }.get(demand_bucket, 0)

    # Reputación: permite premium sostenido
    score += {
        "strong": 10,
        "good": 5,
        "weak": -2,
        "poor": -10,
        None: 0,
    }.get(reputation_bucket, 0)

    # Visibilidad: si es baja, la subida puede fallar (soft penalty)
    score += {
        "good": 8,
        "medium": 3,
        "low": -18,
        None: 0,
    }.get(visibility_bucket, 0)

    # Eventos: empuje de demanda
    if event_pressure is not None:
        score += (event_pressure * 10)  # 0..10

    # Paridad warning: reduce seguridad
    if parity_status == "warning":
        score -= 8

    return _clamp_0_100(score)


def _compute_lower_score(normalized: Dict[str, Any]) -> int:
    price_posture = normalized.get("price_posture")
    demand_bucket = normalized.get("demand_bucket")
    reputation_bucket = normalized.get("reputation_bucket")
    visibility_bucket = normalized.get("visibility_bucket")
    event_pressure = normalized.get("event_pressure")
    parity_status = normalized.get("parity_status")

    score = 50

    # Precio: si es caro, hay incentivo a bajar
    score += {
        "very_high": 30,
        "high": 20,
        "aligned": 5,
        "low": -10,
        "very_low": -25,
        None: 0,
    }.get(price_posture, 0)

    # Demanda baja: sostiene la bajada
    score += {
        "very_low": 25,
        "low": 15,
        "medium": 5,
        "high": -10,
        "very_high": -20,
        None: 0,
    }.get(demand_bucket, 0)

    # Reputación: reputación mala exige ajuste a precio
    score += {
        "poor": 10,
        "weak": 5,
        "good": -5,
        "strong": -12,
        None: 0,
    }.get(reputation_bucket, 0)

    # Visibilidad: con visibilidad baja, bajar puede recuperar demanda (soft reward)
    score += {
        "low": 6,
        "medium": 2,
        "good": -6,
        None: 0,
    }.get(visibility_bucket, 0)

    # Eventos: si hay eventos, baja menor necesidad
    if event_pressure is not None:
        score += (0.5 - event_pressure) * 12  # cuando event_pressure alto => lower penalizado

    if parity_status == "warning":
        score -= 6

    return _clamp_0_100(score)


def _suggested_range_for_raise(normalized: Dict[str, Any]) -> Dict[str, Any]:
    price_posture = normalized.get("price_posture")
    demand_bucket = normalized.get("demand_bucket")
    event_pressure = normalized.get("event_pressure")

    if price_posture == "very_low":
        base_min, base_max = 10, 18
    elif price_posture == "low":
        base_min, base_max = 6, 12
    elif price_posture == "aligned":
        base_min, base_max = 3, 6
    else:
        base_min, base_max = 2, 4

    # severidad por demanda/evento
    severity_boost = 0
    if demand_bucket in ("high", "very_high"):
        severity_boost = 3
    if event_pressure is not None and event_pressure >= 0.50:
        severity_boost += 2

    return {
        "range_pct_min": base_min + severity_boost,
        "range_pct_max": base_max + severity_boost,
    }


def _suggested_range_for_lower(normalized: Dict[str, Any]) -> Dict[str, Any]:
    price_posture = normalized.get("price_posture")
    demand_bucket = normalized.get("demand_bucket")
    event_pressure = normalized.get("event_pressure")

    if price_posture == "very_high":
        base_min, base_max = 12, 18
    elif price_posture == "high":
        base_min, base_max = 7, 12
    elif price_posture == "aligned":
        base_min, base_max = 3, 7
    else:
        base_min, base_max = 2, 4

    severity_boost = 0
    if demand_bucket in ("very_low", "low"):
        severity_boost = 3
    if event_pressure is not None and event_pressure <= 0.25:
        severity_boost += 2

    return {
        "range_pct_min": base_min + severity_boost,
        "range_pct_max": base_max + severity_boost,
    }


def _build_guardrails(normalized: Dict[str, Any], decision: str) -> List[str]:
    guardrails: List[str] = []
    parity_status = normalized.get("parity_status")
    visibility_bucket = normalized.get("visibility_bucket")
    price_posture = normalized.get("price_posture")
    demand_bucket = normalized.get("demand_bucket")
    event_pressure = normalized.get("event_pressure")

    if parity_status == "warning":
        guardrails.append("parity_status=warning (vigilancia de best-rate)")
    if visibility_bucket == "low":
        guardrails.append("visibility_bucket=low (revisar distribución antes de subir)")
    if decision == "raise" and price_posture in ("high", "very_high"):
        guardrails.append("evitar raise si postura de precio ya está alta")
    if decision == "lower" and price_posture in ("low", "very_low"):
        guardrails.append("evitar lower si ya estás barato vs compset")
    if decision in ("raise", "lower") and event_pressure is not None and event_pressure >= 0.75:
        guardrails.append("event_pressure alto: confirmar sostenibilidad post-evento")
    if demand_bucket is None:
        guardrails.append("demand_bucket desconocido: mantener revisión más frecuente")

    return guardrails


def decide_pro(normalized: Dict[str, Any]) -> Dict[str, Any]:
    """
    Motor PRO: decision + confidence + suggested_action + reasons + guardrails.
    """
    dq = _data_quality(normalized)

    parity_status = normalized.get("parity_status")
    visibility_bucket = normalized.get("visibility_bucket")
    price_posture = normalized.get("price_posture")

    constraints: List[str] = []
    # Hard constraints
    if parity_status == "violation":
        constraints.append("parity_violation")
        decision = "hold"
        confidence = 25
        return {
            "decision": decision,
            "confidence": confidence,
            "scores": {"raise_score": 0, "lower_score": 0, "gap": 0},
            "reasons": ["parity_status=violation -> hard constraint hold"],
            "guardrails": ["FIX_PARITY / corrección de paridad"],
            "constraints_applied": constraints,
            "data_quality": dq,
            "suggested_action": {
                "primary": "Hold por paridad violada. Prioriza corrección de best-rate.",
                "review_in_hours": 24,
                "guardrails": ["parity_status=violation"],
            },
        }

    critical_missing = dq["critical_missing"]
    if len(critical_missing) > 0:
        constraints.append("missing_critical_data")
        decision = "hold"
        # confidence driven by quality_factor
        confidence = _clamp_0_100(20 + dq["quality_factor"] * 15)  # 20..35
        return {
            "decision": decision,
            "confidence": confidence,
            "scores": {"raise_score": 0, "lower_score": 0, "gap": 0},
            "reasons": [f"missing_critical_data: {', '.join(critical_missing[:4])}"],
            "guardrails": ["no decidir sin datos críticos comparables"],
            "constraints_applied": constraints,
            "data_quality": dq,
            "suggested_action": {
                "primary": "Hold temporal. Faltan datos críticos para decidir con trazabilidad.",
                "review_in_hours": 48,
                "guardrails": [f"missing={', '.join(critical_missing[:4])}"],
            },
        }

    # hard constraint: visibility low + price already low -> hold
    if visibility_bucket == "low" and price_posture in ("very_low", "low"):
        constraints.append("visibility_low_plus_price_low")
        decision = "hold"
        confidence = 32
        return {
            "decision": decision,
            "confidence": confidence,
            "scores": {"raise_score": 0, "lower_score": 0, "gap": 0},
            "reasons": ["visibility_bucket=low y price_posture=low/very_low -> hard constraint hold"],
            "guardrails": ["primero arreglar distribución/visibilidad"],
            "constraints_applied": constraints,
            "data_quality": dq,
            "suggested_action": {
                "primary": "Hold: subir precio con visibilidad baja tiende a fallar.",
                "review_in_hours": 72,
                "guardrails": ["visibility_bucket=low", "price_posture=low/very_low"],
            },
        }

    # compute scores
    raise_score = _compute_raise_score(normalized)
    lower_score = _compute_lower_score(normalized)
    gap = raise_score - lower_score

    # decision
    # Umbrales: gap y mínimo de fuerza
    if gap >= 15 and raise_score >= 70:
        decision = "raise"
    elif gap <= -15 and lower_score >= 70:
        decision = "lower"
    else:
        decision = "hold"

    # confidence driven by quality + gap + consistency
    quality_factor = dq["quality_factor"]
    consistency = _signal_consistency(normalized, decision)

    gap_strength = min(30, abs(gap) * 0.8)  # 0..30
    quality_bonus = quality_factor * 18  # 0..18
    consistency_bonus = consistency * 15  # 0..15
    penalty_for_weak_decision = 0 if decision in ("raise", "lower") else 8

    if decision in ("raise", "lower"):
        conf = 52 + gap_strength + quality_bonus + consistency_bonus - penalty_for_weak_decision
    else:
        # hold: si el gap es pequeño, reduce más
        conf = 44 + (max(0, 12 - abs(gap)) * 1.5) + quality_bonus - penalty_for_weak_decision

    confidence = _clamp_0_100(conf)

    # suggested action
    guardrails = _build_guardrails(normalized, decision)
    if decision == "raise":
        rng = _suggested_range_for_raise(normalized)
        primary = f"RAISE recomendado. Ajuste sugerido: +{rng['range_pct_min']}% a +{rng['range_pct_max']}%."
        review_in_hours = 24 if confidence >= 75 else 48
    elif decision == "lower":
        rng = _suggested_range_for_lower(normalized)
        primary = f"LOWER recomendado. Ajuste sugerido: -{rng['range_pct_min']}% a -{rng['range_pct_max']}%."
        review_in_hours = 24 if confidence >= 75 else 48
    else:
        primary = "HOLD recomendado. Mantener postura y revisar señales (demanda/visibilidad/paridad)."
        review_in_hours = 48 if confidence >= 65 else 72

    # reasons (deterministas y auditables)
    reasons: List[str] = []
    reasons.append(f"parity_status={parity_status}")
    reasons.append(f"price_posture={price_posture}")
    reasons.append(f"demand_bucket={normalized.get('demand_bucket')} (demand_score={normalized.get('demand_score')})")
    reasons.append(f"reputation_bucket={normalized.get('reputation_bucket')} (gri={normalized.get('reputation_gri')})")
    reasons.append(f"visibility_bucket={normalized.get('visibility_bucket')} (visibility_score={normalized.get('visibility_score')})")
    reasons.append(
        f"events_count={normalized.get('events_count')} (event_pressure={normalized.get('event_pressure')})"
    )
    reasons.append(f"raise_score={raise_score} lower_score={lower_score} gap={gap}")
    reasons.append(f"decision={decision}")

    suggested_action = {
        "primary": primary,
        "review_in_hours": review_in_hours,
        "guardrails": guardrails,
    }
    if decision == "raise":
        suggested_action["range_pct_min"] = rng["range_pct_min"]
        suggested_action["range_pct_max"] = rng["range_pct_max"]
    if decision == "lower":
        suggested_action["range_pct_min"] = -rng["range_pct_min"]
        suggested_action["range_pct_max"] = -rng["range_pct_max"]

    return {
        "decision": decision,
        "confidence": confidence,
        "scores": {"raise_score": raise_score, "lower_score": lower_score, "gap": gap},
        "reasons": reasons,
        "guardrails": guardrails,
        "constraints_applied": constraints,
        "data_quality": dq,
        "suggested_action": suggested_action,
        "signals_used": {
            "own_price": normalized.get("own_price"),
            "compset_avg": normalized.get("compset_avg"),
            "price_position_rank": normalized.get("price_position_rank"),
            "price_position_total": normalized.get("price_position_total"),
            "price_rel_diff": normalized.get("price_rel_diff"),
            "price_posture": normalized.get("price_posture"),
            "demand_score": normalized.get("demand_score"),
            "demand_bucket": normalized.get("demand_bucket"),
            "reputation_gri": normalized.get("reputation_gri"),
            "reputation_bucket": normalized.get("reputation_bucket"),
            "visibility_score": normalized.get("visibility_score"),
            "visibility_bucket": normalized.get("visibility_bucket"),
            "parity_status": normalized.get("parity_status"),
            "events_count": normalized.get("events_count"),
            "event_pressure": normalized.get("event_pressure"),
            "can_command_premium": normalized.get("can_command_premium"),
            "distribution_health": normalized.get("distribution_health"),
        },
    }


def build_deterministic_decision_pro(full_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience: full_analysis -> signals(v1) -> normalize(v2) -> derived event_pressure -> decide_pro
    """
    signals = build_signals_from_pipeline(full_analysis)
    normalized = normalize_signals_v2(signals)
    normalized["event_pressure"] = _event_pressure(normalized.get("events_count"))
    # opcional: distribution_health / can_command_premium (informativas, no decision)
    normalized["can_command_premium"] = (
        normalized.get("reputation_bucket") in ("strong", "good")
        and normalized.get("demand_bucket") in ("high", "very_high")
        and normalized.get("visibility_bucket") in ("good", "medium")
    )
    normalized["distribution_health"] = (
        "good"
        if normalized.get("visibility_bucket") in ("good", "medium") and normalized.get("parity_status") != "violation"
        else "needs_attention"
    )
    return decide_pro(normalized)

