"""
RevMax — Núcleo determinista (primer corte)
============================================
Reglas auditable y deterministas para producir:
- decision: raise|hold|lower
- confidence: 0..100
- reasons[]
- suggested_action

Este módulo NO usa LLM.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


_NA_SENTINELS = {"", "?", "No encontrado", "No encontrado.", "null", "None"}


def _is_missing(x: Any) -> bool:
    return x is None or (isinstance(x, str) and x.strip() in _NA_SENTINELS)


def _to_float(x: Any) -> Optional[float]:
    if _is_missing(x):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if s in _NA_SENTINELS:
        return None
    # Extraer el primer número con signo y decimales
    m = re.search(r"-?\d+(?:[.,]\d+)?", s)
    if not m:
        return None
    num = m.group(0).replace(",", ".")
    try:
        return float(num)
    except ValueError:
        return None


def _to_int(x: Any) -> Optional[int]:
    f = _to_float(x)
    if f is None:
        return None
    try:
        return int(round(f))
    except Exception:
        return None


def _parse_price_position(pos: Any) -> Tuple[Optional[int], Optional[int]]:
    """
    Espera algo como:
      "#3 / 12"
      "3/12"
    """
    if _is_missing(pos):
        return None, None
    s = str(pos)
    m = re.search(r"#?\s*(\d+)\s*\/\s*(\d+)", s)
    if not m:
        return None, None
    try:
        return int(m.group(1)), int(m.group(2))
    except Exception:
        return None, None


def _normalize_parity_status(s: Any) -> Optional[str]:
    if _is_missing(s):
        return None
    t = str(s).strip().lower()
    if "violation" in t or "viol" in t:
        return "violation"
    if "warn" in t or "aviso" in t:
        return "warning"
    if t in ("ok", "parity ok", "paridad ok"):
        return "ok"
    # fallback: buscar por keywords
    if "ok" == t:
        return "ok"
    return None


def _normalize_demand_signal(signal: Any) -> Optional[str]:
    if _is_missing(signal):
        return None
    t = str(signal).strip().lower().replace("_", "-")
    if t in ("very-high", "very_high", "muy-alta", "muy-alto"):
        return "very-high"
    if t in ("high", "alta", "alto"):
        return "high"
    if t in ("low", "baja", "bajo"):
        return "low"
    if t in ("medium", "moderate", "moderado", "moderada", "media", "media/estable"):
        return "medium"
    return None


def _visibility_to_0_1(v: Optional[float]) -> Optional[float]:
    if v is None:
        return None
    # Si viene como 0..100, escalar a 0..1
    if v > 1.0:
        v = v / 100.0
    # clamp a [0,1]
    return max(0.0, min(1.0, float(v)))


def _demand_bucket_from_score(score: Optional[float]) -> Optional[str]:
    if score is None:
        return None
    if score >= 85:
        return "very-high"
    if score >= 70:
        return "high"
    if score <= 45:
        return "low"
    return "medium"


def build_signals_from_pipeline(full_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mapea el output real del pipeline hacia un objeto `signals` mínimo.

    Fuentes (prioridad):
    - evidence_found (si existe)
    - agent_outputs.* (si evidence_found falta)
    """
    evidence = full_analysis.get("evidence_found") or {}
    agent_outputs = full_analysis.get("agent_outputs") or {}

    discovery = agent_outputs.get("discovery") or {}
    compset = agent_outputs.get("compset") or {}
    pricing = agent_outputs.get("pricing") or {}
    demand = agent_outputs.get("demand") or {}
    reputation = agent_outputs.get("reputation") or {}
    distribution = agent_outputs.get("distribution") or {}

    # --- evidence_found (si existe) ---
    own_price_raw = evidence.get("own_price")
    compset_avg_raw = evidence.get("compset_avg")
    price_position_raw = evidence.get("price_position")
    demand_score_raw = evidence.get("demand_score")
    reputation_gri_raw = evidence.get("gri")
    visibility_score_raw = evidence.get("visibility")
    parity_status_raw = evidence.get("parity_status")

    # --- agent_outputs (fallback) ---
    own_price_fallback = (
        (discovery.get("adr_double") if discovery else None)
        or None
    )
    compset_avg_fallback = (
        (compset.get("compset_summary") or {}).get("primary_avg_adr")
        if compset else None
    )
    pricing_mc = pricing.get("market_context") or {}
    your_rank_fallback = pricing_mc.get("your_position_rank")
    total_compset_fallback = pricing_mc.get("total_compset")

    demand_index = demand.get("demand_index") or {}
    demand_score_fallback = demand_index.get("score")
    demand_signal_fallback = demand_index.get("signal")

    reputation_gri_fallback = (reputation.get("gri") or {}).get("value")
    distribution_visibility_fallback = distribution.get("visibility_score")
    distribution_parity_fallback = ((distribution.get("rate_parity") or {}) or {}).get("status")

    events_raw = demand.get("events_detected") or []
    events_count = len(events_raw) if isinstance(events_raw, list) else 0
    events_present = events_count > 0

    # demand_signal fallback: si no existe, derivar desde score
    demand_signal_from_evidence = None  # evidence_found no trae demand_signal en este pipeline

    return {
        "own_price": _to_float(own_price_raw) if not _is_missing(own_price_raw) else _to_float(own_price_fallback),
        "compset_avg": _to_float(compset_avg_raw) if not _is_missing(compset_avg_raw) else _to_float(compset_avg_fallback),
        "price_position_rank": _to_int(_parse_price_position(price_position_raw)[0]) if not _is_missing(price_position_raw) else _to_int(your_rank_fallback),
        "price_position_total": _to_int(_parse_price_position(price_position_raw)[1]) if not _is_missing(price_position_raw) else _to_int(total_compset_fallback),
        "demand_score": _to_float(demand_score_raw) if not _is_missing(demand_score_raw) else _to_float(demand_score_fallback),
        "demand_signal": _normalize_demand_signal(demand_signal_from_evidence) or _normalize_demand_signal(demand_signal_fallback),
        "reputation_gri": _to_float(reputation_gri_raw) if not _is_missing(reputation_gri_raw) else _to_float(reputation_gri_fallback),
        "visibility_score": _to_float(visibility_score_raw) if not _is_missing(visibility_score_raw) else _to_float(distribution_visibility_fallback),
        "parity_status": _normalize_parity_status(parity_status_raw) or _normalize_parity_status(distribution_parity_fallback),
        "events_present": events_present,
        "events_count": events_count,
    }


def normalize_signals(signals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza a escalas y categorías fijas para el engine determinista.
    """
    own_price = _to_float(signals.get("own_price"))
    compset_avg = _to_float(signals.get("compset_avg"))
    demand_score = _to_float(signals.get("demand_score"))
    reputation_gri = _to_float(signals.get("reputation_gri"))
    visibility_score = _visibility_to_0_1(_to_float(signals.get("visibility_score")))

    parity_status = _normalize_parity_status(signals.get("parity_status"))

    demand_signal = _normalize_demand_signal(signals.get("demand_signal"))
    if demand_signal is None:
        demand_signal = _demand_bucket_from_score(demand_score)

    price_position_rank = _to_int(signals.get("price_position_rank"))
    price_position_total = _to_int(signals.get("price_position_total"))

    events_present = bool(signals.get("events_present")) if signals.get("events_present") is not None else False
    events_count = _to_int(signals.get("events_count")) or 0

    # derive pressure posture
    rel_diff = None
    price_posture = None
    if own_price is not None and compset_avg not in (None, 0):
        rel_diff = (own_price - compset_avg) / compset_avg
        if rel_diff <= -0.05:
            price_posture = "low"
        elif rel_diff >= 0.05:
            price_posture = "high"
        else:
            price_posture = "aligned"

    demand_bucket = None
    if demand_score is not None:
        demand_bucket = _demand_bucket_from_score(demand_score)

    return {
        "own_price": own_price,
        "compset_avg": compset_avg,
        "price_posture": price_posture,
        "price_rel_diff": rel_diff,
        "price_position_rank": price_position_rank,
        "price_position_total": price_position_total,
        "demand_score": demand_score,
        "demand_signal": demand_signal,
        "demand_bucket": demand_bucket,
        "reputation_gri": reputation_gri,
        "visibility_score": visibility_score,
        "visibility_low": visibility_score is not None and visibility_score < 0.5,
        "parity_status": parity_status,
        "events_present": events_present,
        "events_count": events_count,
    }


def decide(normalized: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplica reglas deterministas:
    - parity violation -> hold
    - visibility low + price low -> hold
    - price low + demand high -> raise
    - price high + demand low -> lower
    - default hold
    """
    base = 50

    missing_critical = any(
        normalized.get(k) is None
        for k in ("own_price", "compset_avg", "demand_score")
    )
    if missing_critical:
        return {
            "decision": "hold",
            "confidence": 20,
            "suggested_action": {"primary": "Revisar datos antes de decidir.", "review_in_hours": 24},
        }

    parity_status = normalized.get("parity_status")
    visibility_low = normalized.get("visibility_low", False)
    price_posture = normalized.get("price_posture")
    demand_bucket = normalized.get("demand_bucket") or normalized.get("demand_signal")

    decision = "hold"
    conf = base
    guardrails: List[str] = []

    # Regla 1
    if parity_status == "violation":
        decision = "hold"
        conf -= 25
        guardrails.append("Paridad violada: priorizar resolver paridad.")
    # Regla 2
    elif visibility_low and price_posture == "low":
        decision = "hold"
        conf -= 15
        guardrails.append("Visibilidad baja + precio bajo: evitar subida sin mejora de distribución.")
    # Regla 3
    elif price_posture == "low" and demand_bucket == "high":
        decision = "raise"
        conf += 20
    # Regla 4
    elif price_posture == "high" and demand_bucket == "low":
        decision = "lower"
        conf += 20

    # Bonuses por concordancia (solo si no está en reglas de restricción)
    if decision == "raise":
        if price_posture == "low":
            conf += 20
        if demand_bucket == "high":
            conf += 10
        if isinstance(normalized.get("reputation_gri"), (int, float)) and normalized.get("reputation_gri") >= 80:
            conf += 5
    elif decision == "lower":
        if price_posture == "high":
            conf += 20
        if demand_bucket == "low":
            conf += 10
    elif decision == "hold":
        # hold "razonable"
        if price_posture == "aligned":
            conf += 10
        if demand_bucket == "medium":
            conf += 10

    # Penalizaciones extra
    if visibility_low:
        conf -= 10

    # clamp
    conf = int(max(0, min(100, conf)))

    suggested = {
        "primary": (
            "Subir ligeramente el precio (p.ej. +5% a +10%)."
            if decision == "raise"
            else "Mantener el precio actual."
            if decision == "hold"
            else "Bajar ligeramente el precio (p.ej. -5% a -10%)."
        ),
        "review_in_hours": 48 if decision in ("raise", "lower") else 24,
        "guardrails": guardrails,
    }
    return {"decision": decision, "confidence": conf, "suggested_action": suggested}


def build_reasons(normalized: Dict[str, Any], decision: str) -> List[str]:
    reasons: List[str] = []

    parity_status = normalized.get("parity_status")
    if parity_status:
        reasons.append(f"parity_status={parity_status}")
    visibility_score = normalized.get("visibility_score")
    if visibility_score is not None:
        reasons.append(f"visibility_score={visibility_score:.2f}")
        if normalized.get("visibility_low"):
            reasons.append("visibilidad baja (<0.5)")

    own_price = normalized.get("own_price")
    compset_avg = normalized.get("compset_avg")
    rel_diff = normalized.get("price_rel_diff")
    if own_price is not None and compset_avg is not None and rel_diff is not None:
        reasons.append(f"own_price={own_price} vs compset_avg={compset_avg} (diff={rel_diff*100:+.1f}%)")
        reasons.append(f"price_posture={normalized.get('price_posture')}")

    demand_bucket = normalized.get("demand_bucket") or normalized.get("demand_signal")
    if demand_bucket:
        reasons.append(f"demand_bucket={demand_bucket} (score={normalized.get('demand_score')})")

    # Regla disparadora (explicación mínima, determinista)
    if parity_status == "violation":
        reasons.append("Regla: paridad violation -> hold")
    elif normalized.get("visibility_low") and normalized.get("price_posture") == "low":
        reasons.append("Regla: visibilidad baja + precio bajo -> hold")
    elif normalized.get("price_posture") == "low" and demand_bucket == "high":
        reasons.append("Regla: precio bajo + demanda alta -> raise")
    elif normalized.get("price_posture") == "high" and demand_bucket == "low":
        reasons.append("Regla: precio alto + demanda baja -> lower")
    else:
        reasons.append("Regla: default -> hold")

    # Eventos solo como reason informativa (no cambia reglas en este primer corte)
    if normalized.get("events_present"):
        reasons.append(f"events_present=true (count={normalized.get('events_count')})")

    # Decision final
    reasons.append(f"decision={decision}")
    return reasons

