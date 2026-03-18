"""
RevMax — Decision Comparison (legacy vs deterministic PRO)
============================================================
Construye un bloque audit-able para comparar:
- legacy_decision: consolidated_price_action (actual pipeline)
- deterministic_pro_decision: deterministic_decision_pro.decision

Salida:
{
  "legacy_decision": "raise|hold|lower|unknown",
  "deterministic_pro_decision": "raise|hold|lower|unknown",
  "match": bool,
  "difference_type": "...",
  "comment": "...",
  "legacy_reasons": [...],
  "pro_reasons": [...],
  "constraints_applied": [...],
  "missing_data": [...]
}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _normalize_action(action: Any) -> str:
    if not isinstance(action, str):
        return "unknown"
    t = action.strip().lower()
    if t in ("raise", "hold", "lower"):
        return t
    # tolerar variantes comunes
    if "up" in t:
        return "raise"
    if "down" in t:
        return "lower"
    if "stay" in t or "keep" in t:
        return "hold"
    return "unknown"


def _difference_type(legacy: str, pro: str) -> str:
    if legacy == pro and legacy != "unknown":
        return "same_decision"

    mapping = {
        ("raise", "hold"): "legacy_raise_vs_pro_hold",
        ("hold", "raise"): "legacy_hold_vs_pro_raise",
        ("hold", "lower"): "legacy_hold_vs_pro_lower",
        ("lower", "hold"): "legacy_lower_vs_pro_hold",
        ("raise", "lower"): "legacy_raise_vs_pro_lower",
        ("lower", "raise"): "legacy_lower_vs_pro_raise",
    }
    return mapping.get((legacy, pro), "unknown_difference")


def build_decision_comparison(full_analysis: Dict[str, Any]) -> Dict[str, Any]:
    briefing = full_analysis.get("briefing") or {}
    legacy_action = briefing.get("consolidated_price_action") or briefing.get("consolidated_action") or "hold"

    pro_bundle = full_analysis.get("deterministic_decision_pro") or {}
    pro_action = pro_bundle.get("decision") or "unknown"

    legacy_decision = _normalize_action(legacy_action)
    deterministic_pro_decision = _normalize_action(pro_action)
    match = legacy_decision == deterministic_pro_decision and legacy_decision != "unknown"

    difference_type = _difference_type(legacy_decision, deterministic_pro_decision)

    # Razones / restricciones
    pro_reasons: List[str] = pro_bundle.get("reasons") if isinstance(pro_bundle.get("reasons"), list) else []
    pro_constraints: List[str] = pro_bundle.get("constraints_applied") if isinstance(pro_bundle.get("constraints_applied"), list) else []

    legacy_decision_drivers = briefing.get("decision_drivers") or briefing.get("decision_drivers_list") or []
    legacy_reasons: List[str] = []
    if isinstance(legacy_decision_drivers, list):
        for item in legacy_decision_drivers:
            if isinstance(item, dict):
                txt = item.get("rationale") or item.get("message") or item.get("reason") or item.get("type")
                if txt:
                    legacy_reasons.append(str(txt))
            elif isinstance(item, str):
                legacy_reasons.append(item)

    if not legacy_reasons:
        # backup: consolidación
        cons = briefing.get("consolidation_rationale")
        if cons:
            legacy_reasons = [str(cons)[:500]]

    # missing data flags (si el pro tuvo missing_critical o fallback)
    missing_data: List[str] = []
    pro_dq = pro_bundle.get("data_quality") or {}
    if isinstance(pro_dq, dict):
        missing = pro_dq.get("critical_missing") or []
        if isinstance(missing, list):
            missing_data = [str(x) for x in missing][:10]

    comment = (
        "Las decisiones coinciden usando señales deterministas y la consolidación legacy."
        if match
        else f"Legacy={legacy_decision} vs PRO={deterministic_pro_decision}. difference_type={difference_type}."
    )

    return {
        "legacy_decision": legacy_decision,
        "deterministic_pro_decision": deterministic_pro_decision,
        "match": match,
        "difference_type": difference_type,
        "comment": comment,
        "legacy_reasons": legacy_reasons[:20],
        "pro_reasons": pro_reasons[:20],
        "constraints_applied": pro_constraints[:20],
        "missing_data": missing_data,
    }

