"""
RevMax — QA Registry
====================
Persistencia de casos de validación en data/qa_runs/.
Funciones: save, load, summarize, apply_human_review.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from qa_case_builder import _slug


def _qa_runs_dir(base_dir: Optional[str] = None) -> str:
    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "data", "qa_runs")


def save_validation_case(
    case: dict,
    base_dir: Optional[str] = None,
) -> str:
    """
    Guarda el caso en data/qa_runs/<timestamp>_<hotel_slug>.json.
    Devuelve la ruta absoluta del archivo escrito.
    """
    directory = _qa_runs_dir(base_dir)
    os.makedirs(directory, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    hotel_slug = _slug(case.get("hotel_name", "unknown"))
    filename = f"{ts}_{hotel_slug}.json"
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(case, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    return path


def load_validation_cases(
    base_dir: Optional[str] = None,
    limit: int = 100,
) -> List[dict]:
    """
    Carga casos desde data/qa_runs/, ordenados por nombre (timestamp) descendente.
    limit: máximo número de casos a devolver.
    """
    directory = _qa_runs_dir(base_dir)
    if not os.path.isdir(directory):
        return []
    files = []
    for name in os.listdir(directory):
        if name.endswith(".json") and not name.startswith("."):
            path = os.path.join(directory, name)
            if os.path.isfile(path):
                files.append(path)
    files.sort(reverse=True)
    cases = []
    for path in files[:limit]:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            data["_path"] = path
            cases.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return cases


def summarize_validation_cases(
    cases: List[dict],
) -> dict:
    """
    Resumen de una lista de casos: conteo, hoteles únicos, rangos de fechas.
    """
    if not cases:
        return {"count": 0, "hotels": [], "timestamp_min": None, "timestamp_max": None}
    hotels = list({c.get("hotel_name") for c in cases if c.get("hotel_name")})
    timestamps = [c.get("timestamp") for c in cases if c.get("timestamp")]
    return {
        "count": len(cases),
        "hotels": hotels,
        "timestamp_min": min(timestamps) if timestamps else None,
        "timestamp_max": max(timestamps) if timestamps else None,
    }


def apply_human_review(
    case_path: str,
    score: Optional[int] = None,
    feedback: Optional[str] = None,
    verdict: Optional[str] = None,
    adjustment_decision: Optional[str] = None,
) -> dict:
    """
    Actualiza un caso existente con la revisión humana.
    case_path: ruta al JSON del caso.
    score: 1-5 (human_score).
    feedback: texto libre (human_feedback).
    verdict: agree | partial | disagree (human_verdict).
    adjustment_decision: ej. adjust_thresholds, no_change_needed, etc.
    Devuelve el caso actualizado.
    """
    if not os.path.isfile(case_path):
        raise FileNotFoundError(f"Case file not found: {case_path}")
    with open(case_path, encoding="utf-8") as f:
        case = json.load(f)
    if score is not None:
        s = int(score)
        if not 1 <= s <= 5:
            raise ValueError("human_score must be between 1 and 5")
        case["human_score"] = s
    if feedback is not None:
        case["human_feedback"] = str(feedback).strip()
    if verdict is not None:
        v = str(verdict).strip().lower()
        if v not in ("agree", "partial", "disagree"):
            raise ValueError("human_verdict must be one of: agree, partial, disagree")
        case["human_verdict"] = v
    if adjustment_decision is not None:
        case["adjustment_decision"] = str(adjustment_decision).strip()
    with open(case_path, "w", encoding="utf-8") as f:
        json.dump(case, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    return case


def build_qa_decision_summary(records: List[dict]) -> dict:
    """
    Resumen para decisión a partir de una lista de casos (con o sin human review):
    - issues más repetidos (desde triage)
    - media de human_score
    - porcentaje agree / partial / disagree
    - áreas más problemáticas
    - siguiente ajuste recomendado
    """
    from collections import Counter
    from qa_triage import triage_case, ISSUE_LABELS, ADJUSTMENT_LABELS, NO_CHANGE_NEEDED

    if not records:
        return {
            "total_cases": 0,
            "human_score_mean": None,
            "human_verdict_pct": None,
            "most_common_issues": [],
            "most_problematic_areas": [],
            "recommended_next_adjustment": None,
        }

    scores = [r.get("human_score") for r in records if r.get("human_score") is not None]
    verdicts = [r.get("human_verdict") for r in records if r.get("human_verdict")]
    human_score_mean = round(sum(scores) / len(scores), 2) if scores else None
    total_v = len(verdicts)
    if total_v:
        agree = sum(1 for v in verdicts if v == "agree")
        partial = sum(1 for v in verdicts if v == "partial")
        disagree = sum(1 for v in verdicts if v == "disagree")
        human_verdict_pct = {
            "agree": round(100 * agree / total_v, 1),
            "partial": round(100 * partial / total_v, 1),
            "disagree": round(100 * disagree / total_v, 1),
        }
    else:
        human_verdict_pct = None

    issue_counter = Counter()
    adjustment_counter = Counter()
    for r in records:
        t = triage_case(r)
        for i in t.get("issues_detected") or []:
            issue_counter[i] += 1
        for a in t.get("suggested_adjustments") or []:
            if a != NO_CHANGE_NEEDED:
                adjustment_counter[a] += 1

    most_common_issues = [
        {"issue": k, "label": ISSUE_LABELS.get(k, k), "count": v}
        for k, v in issue_counter.most_common(5)
    ]
    most_problematic_areas = most_common_issues

    rec_adj = adjustment_counter.most_common(1)
    recommended_next_adjustment = None
    if rec_adj:
        code = rec_adj[0][0]
        recommended_next_adjustment = {"code": code, "label": ADJUSTMENT_LABELS.get(code, code), "count": rec_adj[0][1]}

    return {
        "total_cases": len(records),
        "human_score_mean": human_score_mean,
        "human_verdict_pct": human_verdict_pct,
        "most_common_issues": most_common_issues,
        "most_problematic_areas": most_problematic_areas,
        "recommended_next_adjustment": recommended_next_adjustment,
    }
