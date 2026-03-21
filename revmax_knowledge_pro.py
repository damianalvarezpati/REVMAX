"""
RevMax — Knowledge layer for deterministic PRO engine
======================================================
Applies only rules from `data/knowledge/candidate_rules.json` with support
in {"strong", "partial"}. Hypothetical / green rules (e.g. EVT-001) are never applied.

Traceability: each applied rule adds structured entries + reason strings tagged with rule id.

Embedded fallbacks: empirical bucket table matches candidate_rules.json so tests stay stable
if the JSON file is missing at runtime.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --- Frozen empirical table (HB-001 / proposed_buckets_summary) ---
EMPIRICAL_LEAD_TIME_BUCKETS: List[Dict[str, Any]] = [
    {"lead_time_range": [0, 7], "n": 19746, "cancellation_rate": 0.0963},
    {"lead_time_range": [8, 30], "n": 18960, "cancellation_rate": 0.2786},
    {"lead_time_range": [31, 90], "n": 29553, "cancellation_rate": 0.377},
    {"lead_time_range": [91, 180], "n": 26439, "cancellation_rate": 0.4471},
    {"lead_time_range": [181, 9999], "n": 24692, "cancellation_rate": 0.5701},
]

# Weekend median premium ratio (CT-001)
WEEKEND_PREMIUM_RATIO = 1.0373

_CANDIDATE_RULES_PATH = Path(__file__).resolve().parent / "data" / "knowledge" / "candidate_rules.json"


def _load_applicable_rule_ids() -> List[str]:
    """Rule ids that may be applied (exclude hypothetical)."""
    ids: List[str] = []
    path = _CANDIDATE_RULES_PATH
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for r in data.get("rules") or []:
                if r.get("support") in ("strong", "partial"):
                    rid = r.get("id")
                    if rid:
                        ids.append(str(rid))
        except (OSError, json.JSONDecodeError):
            pass
    if not ids:
        ids = ["HB-001", "AB-001", "CT-001", "OTA-001", "RV-001"]
    return ids


APPLICABLE_RULE_IDS = frozenset(_load_applicable_rule_ids())


def lead_time_cancel_pressure_tier(lead_time_days: Optional[float]) -> Optional[str]:
    """
    Map lead time (days) to cancellation-pressure tier from empirical hotel_bookings buckets.
    Returns None if lead_time unknown.
    """
    if lead_time_days is None:
        return None
    try:
        lt = float(lead_time_days)
    except (TypeError, ValueError):
        return None
    if lt < 0:
        return None
    for b in EMPIRICAL_LEAD_TIME_BUCKETS:
        lo, hi = b["lead_time_range"]
        if lo <= lt <= hi:
            cr = float(b["cancellation_rate"])
            if cr < 0.15:
                return "low"
            if cr < 0.34:
                return "medium"
            if cr < 0.42:
                return "elevated"
            if cr < 0.52:
                return "high"
            return "very_high"
    return "very_high"


def _review_divergence(
    reviewer_score_0_10: Optional[float], hotel_avg_0_10: Optional[float]
) -> Optional[Tuple[float, str]]:
    """Returns (abs_diff, label) for RV-001; None if cannot compute."""
    if reviewer_score_0_10 is None or hotel_avg_0_10 is None:
        return None
    try:
        r = float(reviewer_score_0_10)
        h = float(hotel_avg_0_10)
    except (TypeError, ValueError):
        return None
    d = abs(r - h)
    if d > 1.0:
        return d, "strong_divergence"
    if d > 0.5:
        return d, "moderate_divergence"
    return None


def compute_knowledge_adjustments(normalized: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic adjustments from integrated knowledge rules.

    Returns:
      raise_delta, lower_delta, confidence_delta (int/float, applied with clamp),
      guardrail_additions, reason_lines, knowledge_applied (list of dicts)
    """
    raise_d = 0
    lower_d = 0
    conf_d = 0.0
    guardrails: List[str] = []
    reasons: List[str] = []
    applied: List[Dict[str, Any]] = []

    lt = normalized.get("lead_time_days")
    tier = lead_time_cancel_pressure_tier(_to_float_safe(lt))
    if tier is not None and "HB-001" in APPLICABLE_RULE_IDS:
        # Longer horizon -> higher empirical cancel rate -> soften appetite for aggressive raises
        if tier == "medium":
            raise_d -= 2
            conf_d -= 1.0
        elif tier == "elevated":
            raise_d -= 3
            conf_d -= 2.0
            guardrails.append(
                "HB-001: ventana de reserva amplía; riesgo de cancelación empíricamente mayor — validar overbooking/overrides"
            )
        elif tier == "high":
            raise_d -= 5
            conf_d -= 3.0
            guardrails.append(
                "HB-001: lead time largo asociado a tasa de cancelación alta en datos hotel_bookings; tratar demanda como menos fija"
            )
        elif tier == "very_high":
            raise_d -= 6
            conf_d -= 4.0
            guardrails.append(
                "HB-001: presión de cancelación muy alta (bucket empírico); cautela en subidas agresivas"
            )
        # tier "low": no penalty (short horizon)
        reasons.append(
            f"HB-001[strong]: lead_time_days={lt} -> cancel_pressure_tier={tier} "
            f"(tabla empírica lead_time vs cancellation_rate, hotel_bookings)"
        )
        applied.append(
            {
                "id": "HB-001",
                "support": "strong",
                "source": "data/knowledge/candidate_rules.json#proposed_buckets_summary.demand_bucket",
                "signal": {"lead_time_days": lt, "cancel_pressure_tier": tier},
            }
        )

    weekend = normalized.get("weekend_context")
    if weekend is True and "CT-001" in APPLICABLE_RULE_IDS:
        reasons.append(
            f"CT-001[strong]: contexto fin de semana — premium medio observado multi-ciudad ~{(WEEKEND_PREMIUM_RATIO - 1) * 100:.1f}% vs entresemana "
            f"(median_weekend_premium_ratio={WEEKEND_PREMIUM_RATIO}; pricing_context_patterns)"
        )
        applied.append(
            {
                "id": "CT-001",
                "support": "strong",
                "source": "data/knowledge/candidate_rules.json + pricing_context_patterns",
                "signal": {"weekend_context": True},
            }
        )

    rev_h = _to_float_safe(normalized.get("hotel_avg_review_0_10"))
    rev_r = _to_float_safe(normalized.get("reviewer_avg_score_0_10"))
    div = _review_divergence(rev_r, rev_h)
    if div is not None and "RV-001" in APPLICABLE_RULE_IDS:
        _diff, label = div
        if label == "strong_divergence":
            conf_d -= 4.0
            guardrails.append(
                "RV-001: divergencia fuerte entre puntuación reseñas recientes y media hotel — revisar calidad/actualidad del GRI antes de premium"
            )
        else:
            conf_d -= 2.0
            guardrails.append(
                "RV-001: posible desalineación moderada reseña vs media hotel (señal de calidad de dato)"
            )
        reasons.append(
            f"RV-001[strong]: |reviewer_avg - hotel_avg|={_diff:.2f} ({label}) "
            f"(correlación reviewer vs hotel score en muestra grande; reputación)"
        )
        applied.append(
            {
                "id": "RV-001",
                "support": "strong",
                "source": "data/knowledge/candidate_rules.json + reputation_patterns",
                "signal": {"reviewer_avg_score_0_10": rev_r, "hotel_avg_review_0_10": rev_h},
            }
        )

    # AB-001 partial: price vs reviews association (weak) — small nudge only
    price_posture = normalized.get("price_posture")
    reputation_bucket = normalized.get("reputation_bucket")
    if "AB-001" in APPLICABLE_RULE_IDS:
        if price_posture in ("high", "very_high") and reputation_bucket in ("poor", "weak"):
            lower_d += 3
            reasons.append(
                "AB-001[partial]: postura de precio alta con reputación débil — refuerzo moderado a bajar "
                "(Airbnb price–rating association r≈0.09; no driver único)"
            )
            applied.append(
                {
                    "id": "AB-001",
                    "support": "partial",
                    "source": "data/knowledge/candidate_rules.json",
                    "signal": {"price_posture": price_posture, "reputation_bucket": reputation_bucket},
                }
            )
        elif price_posture in ("very_low", "low") and reputation_bucket in ("strong", "good"):
            raise_d += 2
            reasons.append(
                "AB-001[partial]: precio bajo con reputación sólida — refuerzo moderado a subir "
                "(evidencia débil; coherencia precio–reseñas)"
            )
            applied.append(
                {
                    "id": "AB-001",
                    "support": "partial",
                    "source": "data/knowledge/candidate_rules.json",
                    "signal": {"price_posture": price_posture, "reputation_bucket": reputation_bucket},
                }
            )

    ota_km = _to_float_safe(normalized.get("ota_search_distance_km"))
    if ota_km is not None and "OTA-001" in APPLICABLE_RULE_IDS:
        conf_d -= 1.0
        reasons.append(
            f"OTA-001[partial, secondary]: distancia búsqueda={ota_km} km como contexto OTA débil "
            f"(r≈-0.03 vs booking; no usar como driver principal de precio)"
        )
        applied.append(
            {
                "id": "OTA-001",
                "support": "partial",
                "source": "data/knowledge/candidate_rules.json + compset_proxy_patterns",
                "signal": {"ota_search_distance_km": ota_km},
            }
        )

    return {
        "raise_delta": raise_d,
        "lower_delta": lower_d,
        "confidence_delta": conf_d,
        "guardrail_additions": guardrails,
        "reason_lines": reasons,
        "knowledge_applied": applied,
    }


def _to_float_safe(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def weekend_range_adjustment_pct(decision: str, weekend_context: Any) -> int:
    """CT-001: mild widening of suggested raise range on weekends (cap +1 point each side)."""
    if decision != "raise" or weekend_context is not True:
        return 0
    if "CT-001" not in APPLICABLE_RULE_IDS:
        return 0
    return 1
