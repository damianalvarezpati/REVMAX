"""
RevMax — Dojo Knowledge Inputs layer
======================================
Calcula por área: cobertura (datasets + artefactos), calidad (reglas + muestras),
validación humana (ledger + qa_runs), readiness en motor PRO, y huecos accionables.

Fuentes:
- data/knowledge/knowledge_areas_config.json
- data/knowledge/candidate_rules.json
- data/knowledge/*_patterns.json (existencia + métricas ligeras)
- data/datasets/MASTER_DATASET_INDEX.json
- data/knowledge/dojo_validation_ledger.json
- data/qa_runs/*.json (casos reales con revisión humana)
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
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


def _support_weight(support: str) -> float:
    s = (support or "").lower()
    if s == "strong":
        return 1.0
    if s == "partial":
        return 0.55
    if s == "hypothetical":
        return 0.0
    return 0.25


def _rule_matches_area(rule: dict, substrings: List[str]) -> bool:
    applies = rule.get("applies_to") or []
    text = " ".join(str(x).lower() for x in applies)
    return any(sub.lower() in text for sub in substrings)


def _dataset_matches_flags(ds: dict, flags: dict) -> bool:
    if not flags:
        return False
    for key, val in flags.items():
        if key == "domain_in":
            if ds.get("domain") not in val:
                return False
        elif key == "name_substrings_any":
            name = (ds.get("name") or "").lower()
            if not any(s.lower() in name for s in val):
                return False
        else:
            if ds.get(key) != val:
                return False
    return True


def _dataset_calendar_seasonality(ds: dict) -> bool:
    name = (ds.get("name") or "").lower()
    if ds.get("domain") == "airbnb":
        return True
    if ds.get("pricing_relevant") and any(
        x in name for x in ("calendar", "weekday", "weekend", "season", "month")
    ):
        return True
    return False


def _dataset_ota_visibility(ds: dict) -> bool:
    if ds.get("domain") == "ota":
        return True
    name = (ds.get("name") or "").lower()
    if ds.get("compset_relevant") and any(
        x in name for x in ("expedia", "booking.com", "ota", "channel", "tripadvisor")
    ):
        return True
    return False


def _count_datasets_for_area(ds_list: List[dict], spec: dict) -> Tuple[int, int]:
    """Returns (count, approx_total_rows for those datasets)."""
    pred = spec.get("dataset_predicate")
    flags = spec.get("dataset_flags")
    rows_sum = 0
    n = 0
    for ds in ds_list:
        ok = False
        if pred == "calendar_seasonality":
            ok = _dataset_calendar_seasonality(ds)
        elif pred == "ota_visibility":
            ok = _dataset_ota_visibility(ds)
        elif flags:
            ok = _dataset_matches_flags(ds, flags)
        if ok:
            n += 1
            r = ds.get("rows")
            if isinstance(r, int) and r > 0:
                rows_sum += min(r, 5_000_000)
    return n, rows_sum


def _pattern_metrics(path: Path) -> Tuple[bool, Optional[int]]:
    if not path.is_file():
        return False, None
    data = _load_json(path)
    if not data:
        return True, None
    # Heurística: claves con listas grandes o stats
    n = 0
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                n += len(v)
            elif isinstance(v, dict) and "n" in v:
                try:
                    n += int(v["n"])
                except (TypeError, ValueError):
                    pass
    return True, n if n else None


def _accepted_knowledge_counts_by_area(base: Path) -> Dict[str, int]:
    p = base / "data/knowledge/refresh/accepted_knowledge.jsonl"
    c: Dict[str, int] = {}
    if not p.is_file():
        return c
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            o = json.loads(line)
            ak = o.get("area_key") or "_unknown"
            c[ak] = c.get(ak, 0) + 1
    except (OSError, json.JSONDecodeError):
        pass
    return c


def _accepted_quality_bonus_for_area(base: Path, area_key: str) -> float:
    """
    Bonus acotado a quality_score según accepted_knowledge: peso alto solo con
    knowledge_type + linked_rule_or_hypothesis; entradas legacy o sin linkage valen poco.
    """
    p = base / "data/knowledge/refresh/accepted_knowledge.jsonl"
    cfg = _load_json(base / "data/knowledge/refresh/knowledge_refresh_config.json") or {}
    sq = cfg.get("accepted_quality_scoring") or {}
    max_pts = float(sq.get("max_quality_bonus_points") or 8.0)
    w_full = float(sq.get("per_accept_with_link_and_type") or 2.0)
    w_partial = float(sq.get("per_accept_partial") or 0.75)
    w_min = float(sq.get("per_accept_minimal") or 0.35)
    if not p.is_file():
        return 0.0
    bonus = 0.0
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            o = json.loads(line)
            if (o.get("area_key") or "_unknown") != area_key:
                continue
            if "knowledge_type" not in o and (o.get("summary") or o.get("reason_for_acceptance")):
                bonus += w_min
                continue
            link = (o.get("linked_rule_or_hypothesis") or "").strip()
            kt = (o.get("knowledge_type") or "").strip()
            if link and kt:
                bonus += w_full
            elif link or kt:
                bonus += w_partial
            else:
                bonus += w_min
    except (OSError, json.JSONDecodeError):
        pass
    return min(max_pts, bonus)


def _refresh_training_candidates_by_area(base: Path) -> Dict[str, int]:
    d = base / "data/dojo/training_candidates"
    out: Dict[str, int] = {}
    if not d.is_dir():
        return out
    for path in d.glob("*.json"):
        data = _load_json(path)
        if not data or data.get("source") != "knowledge_refresh":
            continue
        ak = data.get("area_key")
        if ak:
            out[ak] = out.get(ak, 0) + 1
    return out


def _load_qa_validated(base_dir: Optional[Path] = None) -> Tuple[int, int]:
    """(cases_with_human_score, cases_with_verdict)."""
    base = base_dir or ROOT
    qa_dir = base / "data" / "qa_runs"
    if not qa_dir.is_dir():
        return 0, 0
    with_score = 0
    with_verdict = 0
    for name in os.listdir(qa_dir):
        if not name.endswith(".json"):
            continue
        p = qa_dir / name
        data = _load_json(p)
        if not data:
            continue
        if data.get("human_score") is not None:
            with_score += 1
        if data.get("human_verdict"):
            with_verdict += 1
    return with_score, with_verdict


def _status_from_area_score(score: float) -> str:
    if score < 28:
        return "weak"
    if score < 48:
        return "developing"
    if score < 72:
        return "usable"
    return "strong"


def compute_knowledge_inputs(
    base_dir: Optional[Path] = None,
    write_snapshot: bool = True,
) -> Dict[str, Any]:
    """
    Devuelve dict con areas[], meta, scoring_notes.
    """
    base = base_dir or ROOT
    kn = base / "data" / "knowledge"
    cfg = _load_json(kn / "knowledge_areas_config.json")
    if not cfg:
        return {"error": "missing_config", "areas": []}

    rules_doc = _load_json(kn / "candidate_rules.json")
    rules = (rules_doc or {}).get("rules") or []

    master = _load_json(base / "data" / "datasets" / "MASTER_DATASET_INDEX.json")
    ds_list = (master or {}).get("datasets") or []

    ledger = _load_json(kn / "dojo_validation_ledger.json") or {}
    ledger_areas = (ledger.get("by_area") or {}) if isinstance(ledger, dict) else {}

    targets = cfg.get("targets") or {}
    soft_d = float(targets.get("datasets_soft_cap") or 6)
    soft_v = float(targets.get("validations_soft_cap_per_area") or 12)
    pat_bonus = float(targets.get("pattern_file_bonus_points") or 12)

    engine_ids = set(cfg.get("engine_integrated_rule_ids") or [])

    synthetic_n = int((cfg.get("synthetic_cases") or {}).get("count") or 0)

    qa_score_n, qa_verdict_n = _load_qa_validated(base)
    accepted_by_area = _accepted_knowledge_counts_by_area(base)
    refresh_candidates_by_area = _refresh_training_candidates_by_area(base)

    total_rules_weighted = sum(_support_weight(r.get("support")) for r in rules) or 1.0

    areas_out: List[Dict[str, Any]] = []

    for spec in cfg.get("areas") or []:
        key = spec["area_key"]
        name = spec.get("area_name") or key
        subs = spec.get("rule_applies_to_substrings") or []
        e_ids = spec.get("engine_rule_ids") or []

        # Rules touching this area
        matched_rules: List[dict] = [r for r in rules if _rule_matches_area(r, subs)]
        rules_strong = sum(1 for r in matched_rules if r.get("support") == "strong")
        rules_partial = sum(1 for r in matched_rules if r.get("support") == "partial")
        rules_hyp = sum(1 for r in matched_rules if r.get("support") == "hypothetical")
        rules_supported = rules_strong + rules_partial

        # Datasets
        d_count, d_rows = _count_datasets_for_area(ds_list, spec)

        # Patterns
        pattern_hits = 0
        pattern_depth = 0
        for fn in spec.get("pattern_files") or []:
            pm = _pattern_metrics(kn / fn)
            if pm[0]:
                pattern_hits += 1
                if pm[1]:
                    pattern_depth += min(pm[1], 500_000)

        # Ledger
        la = ledger_areas.get(key) or {}
        ledger_hv = int(la.get("human_validations") or 0)
        ledger_promoted = int(la.get("hypotheses_promoted") or 0)

        # Allocate QA validations across areas by share of supported rules mass
        area_rule_mass = sum(_support_weight(r.get("support")) for r in matched_rules if r.get("support") != "hypothetical")
        share = area_rule_mass / total_rules_weighted if total_rules_weighted else 0.0
        allocated_real = int(round(qa_score_n * share)) if qa_score_n else 0
        validated_cases_count = ledger_hv + allocated_real

        # Synthetic: all mock cases touch multiple dimensions — split evenly for honesty (low per-area)
        n_areas = max(len(cfg.get("areas") or []), 1)
        synthetic_alloc = int(round(synthetic_n / n_areas))
        refresh_tc = int(refresh_candidates_by_area.get(key, 0))
        acc_n = int(accepted_by_area.get(key, 0))

        # --- Scores (0..100), explicit formulas ---
        # Coverage: saturates with dataset count; pattern files add bounded bonus
        cov_raw = 100.0 * (1.0 - math.exp(-0.55 * d_count / max(soft_d, 1.0)))
        cov_raw = min(100.0, cov_raw + min(pat_bonus, pat_bonus * pattern_hits / 2.0))
        coverage_score = round(cov_raw, 1)

        # Quality: strength of rules + log rows (diminishing)
        q_rules = 0.0
        for r in matched_rules:
            q_rules += 100.0 * _support_weight(r.get("support")) / max(len(matched_rules), 1)
        if not matched_rules:
            q_rules = 0.0
        row_factor = min(1.0, math.log1p(d_rows) / math.log1p(2_000_000))
        acc_bonus = _accepted_quality_bonus_for_area(base, key)
        quality_score = round(min(100.0, 0.65 * q_rules + 35.0 * row_factor + acc_bonus), 1)

        # Validation: human loop (ledger + allocated QA) vs target
        val_denom = max(soft_v, 1.0)
        validation_score = round(
            min(
                100.0,
                100.0 * (ledger_hv + allocated_real * 1.15 + ledger_promoted * 2.0) / val_denom,
            ),
            1,
        )

        # Model readiness: reglas PRO cableadas vs esperadas por área
        hooked = [rid for rid in e_ids if rid in engine_ids]
        if e_ids:
            readiness = 100.0 * len(hooked) / len(e_ids)
        else:
            # Sin target explícito en motor: pequeño crédito si hay reglas soportadas, techo bajo
            readiness = min(32.0, 10.0 * rules_supported + 4.0 * pattern_hits)
        model_readiness_score = round(readiness, 1)

        area_score = round(
            0.28 * coverage_score
            + 0.27 * quality_score
            + 0.22 * validation_score
            + 0.23 * model_readiness_score,
            1,
        )

        status_label = _status_from_area_score(area_score)

        missing_gaps: List[str] = []
        suggested_actions: List[str] = []

        if d_count < 2:
            missing_gaps.append("Pocos datasets indexados para esta área en MASTER_DATASET_INDEX.")
            suggested_actions.append("Añadir datasets etiquetados (flags relevant) o actualizar el índice maestro.")
        if pattern_hits < len(spec.get("pattern_files") or []):
            missing_gaps.append("Falta artefacto de patrones extraídos o archivo ausente.")
            suggested_actions.append("Ejecutar scripts/extract_revmax_knowledge.py o restaurar JSON de patrones.")
        if rules_hyp > 0 and rules_supported == 0:
            missing_gaps.append("Solo hipótesis sin soporte empírico en reglas para esta área.")
            suggested_actions.append("Validar con datos o degradar expectativas en el motor.")
        if rules_supported > 0 and len(hooked) < len(e_ids):
            missing_gaps.append("Reglas candidatas no enlazadas al motor determinista PRO.")
            suggested_actions.append("Extender revmax_knowledge_pro / decision_rules_pro para nuevas reglas.")
        if validated_cases_count < 3:
            missing_gaps.append("Validación humana insuficiente (Dojo / qa_runs / ledger).")
            suggested_actions.append("Registrar revisiones en /api/qa/save-validation o subir dojo_validation_ledger.")
        if key == "events" and rules_hyp >= 1:
            missing_gaps.append("Eventos: reglas tipo EVT aún hipotéticas.")
            suggested_actions.append("Enlazar calendario eventos–hotel o validar con series reales antes de pricing.")
        if key == "transport_connectivity" and d_count == 0:
            missing_gaps.append("Sin datasets airline/transport indexados.")
            suggested_actions.append("Ingestar rutas, asientos o conectividad aeroportuaria como features proxy.")

        areas_out.append(
            {
                "area_key": key,
                "area_name": name,
                "datasets_count": d_count,
                "datasets_rows_approx_sum": d_rows,
                "real_cases_count": allocated_real,
                "synthetic_cases_count": synthetic_alloc,
                "refresh_training_candidates_count": refresh_tc,
                "accepted_knowledge_count": acc_n,
                "accepted_quality_bonus_points": round(acc_bonus, 2),
                "validated_cases_count": validated_cases_count,
                "rules_supported_count": rules_supported,
                "rules_strong_count": rules_strong,
                "rules_partial_count": rules_partial,
                "hypotheses_pending_count": rules_hyp,
                "pattern_files_present": pattern_hits,
                "pattern_files_expected": len(spec.get("pattern_files") or []),
                "coverage_score": coverage_score,
                "quality_score": quality_score,
                "validation_score": validation_score,
                "model_readiness_score": model_readiness_score,
                "area_score": area_score,
                "status_label": status_label,
                "missing_gaps": missing_gaps,
                "suggested_actions": suggested_actions,
                "engine_rule_ids_expected": e_ids,
                "engine_rule_ids_active": hooked,
                "rule_ids_in_area": [r.get("id") for r in matched_rules if r.get("id")],
            }
        )

    from knowledge_balancing_engine import enrich_areas_with_knowledge_balance, write_balance_snapshot

    areas_out, balance_summary = enrich_areas_with_knowledge_balance(areas_out, base)

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "meta": {
            "config_path": str(kn / "knowledge_areas_config.json"),
            "rules_path": str(kn / "candidate_rules.json"),
            "master_dataset_index": str(base / "data/datasets/MASTER_DATASET_INDEX.json"),
            "ledger_path": str(kn / "dojo_validation_ledger.json"),
            "balancing_config_path": str(base / "data/knowledge/knowledge_balancing_config.json"),
            "qa_runs_validated_total": qa_score_n,
            "qa_runs_verdict_total": qa_verdict_n,
            "synthetic_cases_total_ui_mock": synthetic_n,
        },
        "knowledge_balance_summary": balance_summary,
        "scoring_notes": {
            "coverage": "100*(1-exp(-0.55*datasets/soft_cap)) + bonus por archivos de patrones presentes.",
            "quality": "Reglas + log(filas) + bonus acotado desde accepted_knowledge (peso alto solo con knowledge_type + linked_rule_or_hypothesis; sin linkage, peso mínimo).",
            "validation": "ledger human_validations + reparto proporcional de qa_runs con human_score vs soft_cap por área.",
            "model_readiness": "ratio de engine_rule_ids integradas en PRO vs esperadas por área (sin ids → techo bajo).",
            "area_score": "0.28*coverage + 0.27*quality + 0.22*validation + 0.23*readiness",
            "knowledge_balance": "Targets por status_label; gap → modo growth/monitor/maintenance; esfuerzo vía recommended_effort_share; validación humana priorizada en déficits y clusters.",
        },
        "areas": areas_out,
    }

    if write_snapshot:
        try:
            write_balance_snapshot(base, areas_out, balance_summary)
            snap = kn / "knowledge_inputs_snapshot.json"
            snap.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    return out


def knowledge_inputs_api_payload(base_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Wrapper estable para HTTP."""
    base = base_dir or ROOT
    payload = compute_knowledge_inputs(base_dir=base, write_snapshot=True)
    try:
        from knowledge_refresh import load_latest_refresh_summary

        kr = load_latest_refresh_summary(base)
        if kr:
            payload["knowledge_refresh"] = kr
    except Exception:
        payload["knowledge_refresh"] = None
    return payload
