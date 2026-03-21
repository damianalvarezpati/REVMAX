"""
RevMax — Knowledge Balancing Engine
====================================
Asignación dinámica de esfuerzo de conocimiento (no uniforme): refuerza áreas débiles,
mantiene las fuertes sin sobre-inversión, y expone prioridades trazables para refresh,
scraping dirigido, ingestión, casos Dojo y validación humana.

No es aprendizaje ingenuo: reglas declarativas + gaps medibles respecto a targets.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent


def _load_json(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_balancing_config(base_dir: Optional[Path] = None) -> dict:
    base = base_dir or ROOT
    p = base / "data/knowledge/knowledge_balancing_config.json"
    return _load_json(p) or {}


def _target_for_area(area: dict, cfg: dict) -> float:
    st = (area.get("status_label") or "usable").lower()
    by_st = cfg.get("target_by_status_label") or {}
    if st in by_st:
        return float(by_st[st])
    return float(cfg.get("global_target_area_score") or 78.0)


def _mode_from_gap(gap: float, thresholds: dict) -> str:
    g_min = float(thresholds.get("growth_gap_min") or 18.0)
    m_max = float(thresholds.get("maintenance_gap_max") or 8.0)
    if gap >= g_min:
        return "growth"
    if gap <= m_max:
        return "maintenance"
    return "monitor"


def _raw_growth_priority(area: dict, gap_score: float, cfg: dict) -> float:
    gw = cfg.get("gap_weights") or {}
    exp = float(gw.get("area_score_exponent") or 1.35)
    eps = float(gw.get("epsilon_uniform") or 0.04)

    base = max(0.0, gap_score) ** exp

    val = float(area.get("validation_score") or 0)
    cov = float(area.get("coverage_score") or 0)
    read = float(area.get("model_readiness_score") or 0)

    v_def = max(0.0, 72.0 - val) / 72.0
    c_def = max(0.0, 65.0 - cov) / 65.0
    r_def = max(0.0, 70.0 - read) / 70.0

    wv = float(gw.get("validation_deficit_weight") or 0.45)
    wc = float(gw.get("coverage_deficit_weight") or 0.25)
    wr = float(gw.get("readiness_deficit_weight") or 0.2)

    return base + wv * v_def * 30.0 + wc * c_def * 20.0 + wr * r_def * 15.0 + eps * 100.0


def _apply_cluster_boost(
    raw_by_key: Dict[str, float],
    gaps_by_key: Dict[str, float],
    clusters: List[List[str]],
    boost: float,
) -> None:
    """Si un miembro del cluster tiene hueco alto, sube prioridad de refuerzo en el cluster."""
    for cl in clusters:
        mg = max((gaps_by_key.get(k, 0.0) for k in cl), default=0.0)
        if mg < 12.0:
            continue
        for k in cl:
            if k in raw_by_key:
                raw_by_key[k] += boost * mg


def _cluster_validation_notes(
    area_key: str,
    gaps_by_key: Dict[str, float],
    clusters: List[List[str]],
) -> List[str]:
    out: List[str] = []
    for cl in clusters:
        if area_key not in cl:
            continue
        weak_peers = [p for p in cl if p != area_key and gaps_by_key.get(p, 0) >= 15.0]
        if weak_peers:
            out.append(
                f"Validación cruzada sugerida: {', '.join(weak_peers)} con brecha ≥15 — "
                f"coordinar revisiones Dojo/QA con {area_key}."
            )
    return out[:3]


def enrich_areas_with_knowledge_balance(
    areas: List[dict],
    base_dir: Optional[Path] = None,
) -> Tuple[List[dict], Dict[str, Any]]:
    """
    Añade a cada área el bloque knowledge_balance y devuelve resumen global.
    """
    base = base_dir or ROOT
    cfg = load_balancing_config(base)
    thresholds = cfg.get("mode_thresholds") or {}
    clusters = cfg.get("reinforcement_clusters") or []
    c_boost = float(cfg.get("cluster_validation_boost") or 0.12)
    temp = float(cfg.get("effort_share_temperature") or 1.15)

    enriched: List[dict] = [dict(a) for a in areas]

    gaps_by_key: Dict[str, float] = {}
    target_by_key: Dict[str, float] = {}
    for a in enriched:
        key = a["area_key"]
        current = float(a.get("area_score") or 0)
        target = _target_for_area(a, cfg)
        gap = max(0.0, min(100.0, target - current))
        gaps_by_key[key] = gap
        target_by_key[key] = target

    raw_by_key: Dict[str, float] = {}
    for a in enriched:
        key = a["area_key"]
        raw_by_key[key] = _raw_growth_priority(a, gaps_by_key[key], cfg)

    _apply_cluster_boost(raw_by_key, gaps_by_key, clusters, c_boost)

    keys = [a["area_key"] for a in enriched]
    raws = [raw_by_key[k] for k in keys]

    if raws:
        m = max(raws)
        exps = [math.exp((r - m) / max(temp, 0.01)) for r in raws]
        s = sum(exps) or 1.0
        shares = [e / s for e in exps]
    else:
        shares = []

    rmin, rmax = (min(raws), max(raws)) if raws else (0.0, 1.0)

    for i, a in enumerate(enriched):
        key = a["area_key"]
        gap = gaps_by_key[key]
        target = target_by_key[key]
        current = float(a.get("area_score") or 0)
        share = shares[i] if i < len(shares) else 1.0 / max(len(enriched), 1)
        mode = _mode_from_gap(gap, thresholds)
        raw = raws[i] if i < len(raws) else 0.0

        if rmax > rmin:
            growth_priority = round(100.0 * (raw - rmin) / (rmax - rmin), 2)
        else:
            growth_priority = 50.0

        val = float(a.get("validation_score") or 0)
        human_validation_priority = round(
            min(1.0, 0.55 * min(1.0, gap / 55.0) + 0.45 * max(0.0, (82.0 - val) / 82.0)),
            4,
        )

        why_parts: List[str] = []
        if gap >= float(thresholds.get("growth_gap_min") or 18.0):
            why_parts.append(f"Brecha vs target ({gap:.1f} pts): priorizar cierre de conocimiento.")
        elif gap <= float(thresholds.get("maintenance_gap_max") or 8.0):
            why_parts.append("Cerca del target: mantenimiento; no dispersar esfuerzo excesivo.")
        else:
            why_parts.append("Seguimiento moderado: consolidar sin campaña agresiva.")

        if a.get("missing_gaps"):
            why_parts.append("Huecos: " + "; ".join((a.get("missing_gaps") or [])[:2]))

        suggested_data: List[str] = []
        if mode == "growth":
            suggested_data.append("Ingesta / indexación de datasets etiquetados para esta área.")
            suggested_data.append("Scraping o HTTP solo desde allowlist con trazabilidad (sin ruido masivo).")
            suggested_data.append("Pipeline extract_revmax_knowledge + revisión de patrones asociados.")
        elif mode == "monitor":
            suggested_data.append("Revisión periódica de MASTER_DATASET_INDEX y artefactos de patrones.")
        else:
            suggested_data.append("Mantenimiento: vigilar regresiones de cobertura y calidad.")

        for s in (a.get("suggested_actions") or [])[:4]:
            if s not in suggested_data:
                suggested_data.append(s)

        human_suggested: List[str] = []
        if human_validation_priority >= 0.42:
            human_suggested.append(
                f"Subir prioridad de validación humana (Dojo / qa_runs / ledger) para {key} "
                f"(validation_score={val:.1f})."
            )
        if gap >= 14.0:
            human_suggested.append(
                "Usar accept-observed con linkage explícito a reglas/hipótesis para anclar calidad."
            )
        human_suggested.extend(_cluster_validation_notes(key, gaps_by_key, clusters))

        kb = {
            "current_area_score": round(current, 2),
            "target_area_score": round(target, 2),
            "knowledge_gap_score": round(gap, 2),
            "growth_priority": growth_priority,
            "mode": mode,
            "growth_mode": mode == "growth",
            "maintenance_mode": mode == "maintenance",
            "recommended_effort_share": round(share, 4),
            "human_validation_priority": human_validation_priority,
            "recommended_actions": [
                "Alinear ingestión de datos + patrones con el gap actual",
                "Asignar validación humana proporcional a human_validation_priority",
            ],
            "why_this_area_needs_attention": " ".join(why_parts)[:1200],
            "suggested_data_actions": suggested_data[:8],
            "suggested_human_validation_actions": human_suggested[:8],
        }
        a["knowledge_balance"] = kb

    summary = {
        "balancing_config_path": str((base / "data/knowledge/knowledge_balancing_config.json").resolve()),
        "areas_in_growth": [a["area_key"] for a in enriched if (a.get("knowledge_balance") or {}).get("mode") == "growth"],
        "areas_in_maintenance": [
            a["area_key"] for a in enriched if (a.get("knowledge_balance") or {}).get("mode") == "maintenance"
        ],
        "total_effort_share_check": round(sum(shares), 4),
    }

    return enriched, summary


def select_areas_for_refresh(
    areas: List[dict],
    max_areas: int,
    *,
    prefer_balance: bool = True,
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Selección dinámica para nightly refresh: orden por growth_priority (gap), no reparto uniforme.
    """
    if not areas or max_areas <= 0:
        return [], {"policy": "empty", "ordered_keys": []}

    if not prefer_balance:
        keys = [a["area_key"] for a in ordered_fallback(areas)]
        return keys[:max_areas], {"policy": "legacy_order", "ordered_keys": keys}

    scored = []
    for a in areas:
        kb = a.get("knowledge_balance") or {}
        gp = float(kb.get("growth_priority") or 0)
        gap = float(kb.get("knowledge_gap_score") or 0)
        scored.append((a["area_key"], gp + gap * 0.02))

    scored.sort(key=lambda x: -x[1])
    ordered_keys = [k for k, _ in scored]
    chosen = ordered_keys[:max_areas]
    return chosen, {
        "policy": "knowledge_balance_priority",
        "ordered_keys": ordered_keys,
        "selected": chosen,
        "rationale": "Orden por growth_priority + gap; tope max_areas — esfuerzo hacia áreas débiles.",
    }


def ordered_fallback(areas: List[dict]) -> List[dict]:
    return sorted(areas, key=lambda a: float(a.get("area_score") or 0))


def dojo_candidate_multiplier_for_area(area: dict, refresh_cfg: dict, n_areas: int) -> float:
    """Multiplicador 1..max para candidatos Dojo según gap y share de esfuerzo."""
    kb = area.get("knowledge_balance") or {}
    share = float(kb.get("recommended_effort_share") or 0)
    gap = float(kb.get("knowledge_gap_score") or 0)
    mode = kb.get("mode") or "monitor"
    mult_max = float(refresh_cfg.get("dojo_effort_multiplier_max") or 2.0)
    uniform = 1.0 / max(n_areas, 1)

    if mode == "maintenance":
        return 1.0
    if mode == "growth":
        t = min(1.0, gap / 42.0) * 0.55 + min(1.0, share / max(uniform, 0.001)) * 0.45
        return round(min(mult_max, 1.0 + t * (mult_max - 1.0)), 2)
    return round(min(1.5, 1.0 + 0.35 * (gap / 100.0)), 2)


def write_balance_snapshot(base: Path, areas: List[dict], summary: Dict[str, Any]) -> None:
    p = base / "data/knowledge/knowledge_balance_snapshot.json"
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        out = {
            "version": 1,
            "summary": summary,
            "by_area": [
                {
                    "area_key": a.get("area_key"),
                    "area_name": a.get("area_name"),
                    "knowledge_balance": a.get("knowledge_balance"),
                }
                for a in areas
            ],
        }
        p.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
