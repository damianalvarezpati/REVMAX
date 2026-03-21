"""
RevMax — Dojo validation debt (operational inbox)
==================================================
La validación humana se modela como deuda acumulada y trabajo pendiente obligatorio,
no como recomendación suave. Las tareas bloquean o penalizan la madurez por área.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def inbox_path(base: Optional[Path] = None) -> Path:
    return (base or ROOT) / "data/dojo/validation_inbox.json"


def debt_config_path(base: Optional[Path] = None) -> Path:
    return (base or ROOT) / "data/dojo/validation_debt_config.json"


def load_debt_config(base: Optional[Path] = None) -> dict:
    return _load_json(debt_config_path(base)) or {}


def load_inbox(base: Optional[Path] = None) -> dict:
    p = inbox_path(base)
    data = _load_json(p)
    if not data:
        return {"version": 1, "updated_at": None, "tasks": []}
    data.setdefault("tasks", [])
    return data


def save_inbox(base: Optional[Path], inbox: dict) -> None:
    _save_json(inbox_path(base), inbox)


def _rule_matches_area(rule: dict, substrings: List[str]) -> bool:
    applies = rule.get("applies_to") or []
    text = " ".join(str(x).lower() for x in applies)
    return any(sub.lower() in text for sub in substrings)


def _tid(prefix: str, *parts: str) -> str:
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{h}"


def _generate_tasks_from_rules(
    base: Path,
    kn_cfg: dict,
    rules: List[dict],
    engine_ids: set,
) -> List[dict]:
    out: List[dict] = []
    for spec in kn_cfg.get("areas") or []:
        key = spec["area_key"]
        subs = spec.get("rule_applies_to_substrings") or []
        e_ids = spec.get("engine_rule_ids") or []
        hooked = [rid for rid in e_ids if rid in engine_ids]
        missing = [rid for rid in e_ids if rid not in engine_ids]

        for r in rules:
            if not _rule_matches_area(r, subs):
                continue
            rid = r.get("id") or ""
            sup = (r.get("support") or "").lower()

            if sup == "hypothetical":
                tid = _tid("hyp", key, rid)
                out.append(
                    {
                        "task_id": tid,
                        "task_type": "hypothesis_review",
                        "area_key": key,
                        "priority": 9,
                        "created_at": _utc_now(),
                        "reason": f"Regla hipotética {rid} requiere validación humana antes de uso en producción.",
                        "linked_hypothesis_id": rid,
                        "linked_case_id": None,
                        "linked_rule_id": rid,
                        "required_for_area_progress": True,
                        "status": "pending",
                        "assigned_to": None,
                    }
                )
            elif sup == "partial":
                tid = _tid("rule", key, rid)
                out.append(
                    {
                        "task_id": tid,
                        "task_type": "rule_review",
                        "area_key": key,
                        "priority": 6,
                        "created_at": _utc_now(),
                        "reason": f"Regla de soporte parcial {rid}: revisión humana obligatoria para acotar confianza.",
                        "linked_hypothesis_id": None,
                        "linked_case_id": None,
                        "linked_rule_id": rid,
                        "required_for_area_progress": False,
                        "status": "pending",
                        "assigned_to": None,
                    }
                )

        for rid in missing:
            tid = _tid("dec", key, rid)
            out.append(
                {
                    "task_id": tid,
                    "task_type": "decision_review",
                    "area_key": key,
                    "priority": 8,
                    "created_at": _utc_now(),
                    "reason": f"Regla {rid} esperada en el área pero no integrada en motor PRO — decisión humana requerida.",
                    "linked_hypothesis_id": None,
                    "linked_case_id": None,
                    "linked_rule_id": rid,
                    "required_for_area_progress": True,
                    "status": "pending",
                    "assigned_to": None,
                }
            )

        # Compset / OTA: deuda explícita si hay hipótesis abiertas en proxy OTA
        if key in ("compset", "ota_visibility"):
            for r in rules:
                if (r.get("support") or "").lower() != "hypothetical":
                    continue
                applies = " ".join(str(x).lower() for x in (r.get("applies_to") or []))
                if "compset" in applies or "ota" in applies or "proxy" in applies:
                    tid = _tid("cmp", key, r.get("id", ""))
                    out.append(
                        {
                            "task_id": tid,
                            "task_type": "compset_review",
                            "area_key": key,
                            "priority": 8,
                            "created_at": _utc_now(),
                            "reason": f"Revisión compset/OTA obligatoria: regla {r.get('id')} sigue hipotética o contextual.",
                            "linked_hypothesis_id": r.get("id"),
                            "linked_case_id": None,
                            "linked_rule_id": r.get("id"),
                            "required_for_area_progress": True,
                            "status": "pending",
                            "assigned_to": None,
                        }
                    )
    return out


def _generate_tasks_from_qa(base: Path) -> List[dict]:
    try:
        from qa_registry import load_validation_cases
    except ImportError:
        return []
    cases = load_validation_cases(str(base), limit=200)
    out: List[dict] = []
    for c in cases:
        if c.get("human_verdict"):
            continue
        path = c.get("_path") or ""
        cid = path or c.get("case_id") or str(uuid.uuid4())[:8]
        tid = _tid("qa", path, str(c.get("timestamp") or ""))
        area = (c.get("area_key") or c.get("primary_area") or "demand") or "demand"
        out.append(
            {
                "task_id": tid,
                "task_type": "validation_case",
                "area_key": area,
                "priority": 7,
                "created_at": _utc_now(),
                "reason": "Caso QA sin veredicto humano — bloque operativo hasta revisión.",
                "linked_hypothesis_id": None,
                "linked_case_id": path,
                "linked_rule_id": None,
                "required_for_area_progress": True,
                "status": "pending",
                "assigned_to": None,
            }
        )
    return out


def _generate_tasks_from_mismatches(base: Path) -> List[dict]:
    p = base / "data/dojo/legacy_pro_mismatches.json"
    doc = _load_json(p) or {}
    out: List[dict] = []
    for i, m in enumerate(doc.get("mismatches") or []):
        area = m.get("area_key") or "_global"
        tid = _tid("mis", area, str(i), str(m.get("signature") or ""))
        out.append(
            {
                "task_id": tid,
                "task_type": "legacy_pro_mismatch",
                "area_key": area,
                "priority": 9,
                "created_at": _utc_now(),
                "reason": m.get("reason") or "Divergencia legacy vs PRO — resolución humana obligatoria.",
                "linked_hypothesis_id": m.get("rule_id"),
                "linked_case_id": m.get("case_ref"),
                "linked_rule_id": m.get("rule_id"),
                "required_for_area_progress": True,
                "status": "pending",
                "assigned_to": None,
            }
        )
    return out


def _generate_tasks_from_refresh(refresh_context: Optional[dict]) -> List[dict]:
    if not refresh_context:
        return []
    obs = refresh_context.get("observations") or []
    out: List[dict] = []
    for o in obs:
        oid = o.get("observed_id") or ""
        if not oid:
            continue
        areas = o.get("area_keys_touched") or [o.get("area_key")] or ["_global"]
        for ak in areas:
            if not ak or ak == "_global":
                continue
            tid = _tid("ref", ak, oid)
            out.append(
                {
                    "task_id": tid,
                    "task_type": "refresh_observation",
                    "area_key": ak,
                    "priority": 6,
                    "created_at": _utc_now(),
                    "reason": f"Knowledge refresh observó señal sin aceptación: {o.get('summary', '')[:200]}",
                    "linked_hypothesis_id": None,
                    "linked_case_id": oid,
                    "linked_rule_id": None,
                    "required_for_area_progress": False,
                    "status": "pending",
                    "assigned_to": None,
                }
            )
    return out


def merge_generated_into_inbox(inbox: dict, generated: List[dict]) -> dict:
    by_id = {t["task_id"]: t for t in inbox.get("tasks", [])}
    for t in generated:
        tid = t["task_id"]
        if tid not in by_id:
            by_id[tid] = t
        else:
            cur = by_id[tid]
            if cur.get("status") == "pending":
                cur["reason"] = t.get("reason") or cur.get("reason")
                cur["priority"] = max(int(cur.get("priority") or 0), int(t.get("priority") or 0))
    inbox["tasks"] = list(by_id.values())
    inbox["updated_at"] = _utc_now()
    return inbox


def sync_validation_inbox(
    base: Optional[Path] = None,
    *,
    refresh_context: Optional[dict] = None,
) -> dict:
    """
    Regenera/une tareas pendientes desde reglas, QA, mismatches y refresh.
    No elimina tareas done/dismissed; actualiza pending existentes.
    """
    base = base or ROOT
    kn = base / "data/knowledge/knowledge_areas_config.json"
    kn_cfg = _load_json(kn) or {}
    rules_doc = _load_json(base / "data/knowledge/candidate_rules.json") or {}
    rules = (rules_doc.get("rules") or []) if isinstance(rules_doc, dict) else []
    engine_ids = set(kn_cfg.get("engine_integrated_rule_ids") or [])

    generated: List[dict] = []
    generated.extend(_generate_tasks_from_rules(base, kn_cfg, rules, engine_ids))
    generated.extend(_generate_tasks_from_qa(base))
    generated.extend(_generate_tasks_from_mismatches(base))
    generated.extend(_generate_tasks_from_refresh(refresh_context))

    inbox = load_inbox(base)
    inbox = merge_generated_into_inbox(inbox, generated)
    save_inbox(base, inbox)
    return inbox


def _pending_tasks(tasks: List[dict]) -> List[dict]:
    return [t for t in tasks if (t.get("status") or "pending") == "pending"]


def compute_debt_metrics(
    inbox: dict,
    base: Optional[Path] = None,
) -> Tuple[dict, Dict[str, dict]]:
    """Métricas globales y por area_key."""
    cfg = load_debt_config(base)
    weights = cfg.get("task_weights") or {}
    overdue_days = int(cfg.get("overdue_days") or 7)
    tasks = inbox.get("tasks") or []
    pending = _pending_tasks(tasks)
    now = datetime.now(timezone.utc)

    per_area: Dict[str, dict] = {}

    def bucket(a: str) -> dict:
        per_area.setdefault(
            a,
            {
                "pending_validation_tasks_count": 0,
                "pending_hypothesis_reviews_count": 0,
                "pending_rule_reviews_count": 0,
                "pending_compset_reviews_count": 0,
                "pending_decision_reviews_count": 0,
                "pending_other_count": 0,
                "required_pending_count": 0,
                "validation_debt_score": 0.0,
                "area_blocked_by_validation": False,
            },
        )
        return per_area[a]

    for t in pending:
        ak = t.get("area_key") or "_global"
        b = bucket(ak)
        tt = t.get("task_type") or ""
        if tt == "validation_case":
            b["pending_validation_tasks_count"] += 1
        elif tt == "hypothesis_review":
            b["pending_hypothesis_reviews_count"] += 1
        elif tt == "rule_review":
            b["pending_rule_reviews_count"] += 1
        elif tt == "compset_review":
            b["pending_compset_reviews_count"] += 1
        elif tt == "decision_review":
            b["pending_decision_reviews_count"] += 1
        else:
            b["pending_other_count"] += 1
        if t.get("required_for_area_progress"):
            b["required_pending_count"] += 1
        w = float(weights.get(tt, 1.0))
        pr = int(t.get("priority") or 5)
        b["validation_debt_score"] += w * (pr / 10.0)

    block_req = int(cfg.get("block_if_required_pending") or 3)
    block_debt = float(cfg.get("block_validation_debt_score") or 72)

    for ak, b in per_area.items():
        raw = b["validation_debt_score"]
        b["validation_debt_score"] = round(min(100.0, raw * 4.0), 1)
        b["area_blocked_by_validation"] = b["required_pending_count"] >= block_req or b["validation_debt_score"] >= block_debt

    overdue = 0
    for t in pending:
        ca = t.get("created_at")
        if not ca:
            continue
        try:
            dt = datetime.fromisoformat(ca.replace("Z", "+00:00"))
            if (now - dt).days >= overdue_days and int(t.get("priority") or 0) >= int(cfg.get("critical_priority_floor") or 7):
                overdue += 1
        except (ValueError, TypeError):
            continue

    areas_blocked = sum(1 for b in per_area.values() if b.get("area_blocked_by_validation"))

    global_m = {
        "dojo_inbox_count": len(pending),
        "overdue_reviews_count": overdue,
        "areas_blocked_count": areas_blocked,
        "pending_by_type": {},
        "pending_validation_tasks": 0,
        "pending_hypothesis_reviews": 0,
        "pending_rule_reviews": 0,
        "pending_compset_reviews": 0,
        "pending_decision_reviews": 0,
        "pending_other": 0,
    }
    for t in pending:
        tt = t.get("task_type") or "unknown"
        global_m["pending_by_type"][tt] = global_m["pending_by_type"].get(tt, 0) + 1
        if tt == "validation_case":
            global_m["pending_validation_tasks"] += 1
        elif tt == "hypothesis_review":
            global_m["pending_hypothesis_reviews"] += 1
        elif tt == "rule_review":
            global_m["pending_rule_reviews"] += 1
        elif tt == "compset_review":
            global_m["pending_compset_reviews"] += 1
        elif tt == "decision_review":
            global_m["pending_decision_reviews"] += 1
        else:
            global_m["pending_other"] += 1

    return global_m, per_area


def apply_validation_debt_to_area_score(
    area_score: float,
    area_key: str,
    per_area: Dict[str, dict],
    base: Optional[Path] = None,
) -> Tuple[float, float, bool]:
    """
    Penaliza madurez si hay deuda crítica. Devuelve (nuevo_area_score, penalty_applied, blocked).
    """
    cfg = load_debt_config(base)
    b = per_area.get(area_key) or {}
    debt = float(b.get("validation_debt_score") or 0)
    blocked = bool(b.get("area_blocked_by_validation"))
    pmax = float(cfg.get("area_score_penalty_max") or 22.0)
    scale = float(cfg.get("debt_to_penalty_scale") or 0.22)
    penalty = min(pmax, debt * scale)
    new_score = max(0.0, float(area_score) - penalty)
    if blocked:
        # Techo adicional: no clasificar como strong si bloqueada
        new_score = min(new_score, 79.0)
    return round(new_score, 1), round(penalty, 2), blocked


def ensure_per_area_metrics(per_area: Dict[str, dict], area_keys: List[str]) -> Dict[str, dict]:
    empty = {
        "pending_validation_tasks_count": 0,
        "pending_hypothesis_reviews_count": 0,
        "pending_rule_reviews_count": 0,
        "pending_compset_reviews_count": 0,
        "pending_decision_reviews_count": 0,
        "pending_other_count": 0,
        "required_pending_count": 0,
        "validation_debt_score": 0.0,
        "area_blocked_by_validation": False,
    }
    for k in area_keys:
        if k not in per_area:
            per_area[k] = dict(empty)
        else:
            for kk, vv in empty.items():
                per_area[k].setdefault(kk, vv)
    return per_area


def mark_validation_tasks_done_for_case_path(base: Optional[Path], case_path: str) -> int:
    """
    Marca done las tareas validation_case cuyo linked_case_id apunta al caso guardado.
    Llamar tras apply_human_review / save-validation.
    """
    if not case_path:
        return 0
    inbox = load_inbox(base)
    n = 0
    try:
        target = Path(case_path).resolve()
    except OSError:
        target = None
    for t in inbox.get("tasks") or []:
        if (t.get("status") or "pending") != "pending":
            continue
        if t.get("task_type") != "validation_case":
            continue
        lid = t.get("linked_case_id") or ""
        if not lid:
            continue
        try:
            tp = Path(lid).resolve()
        except OSError:
            tp = None
        match = False
        if target is not None and tp is not None:
            try:
                match = os.path.samefile(target, tp)
            except OSError:
                match = str(target) == str(tp)
        if not match:
            match = os.path.normpath(str(lid)) == os.path.normpath(str(case_path))
        if match:
            ak = t.get("area_key") or "_global"
            g_before, per_before = compute_debt_metrics(inbox, base)
            debt_before = per_before.get(ak, {}).get("validation_debt_score")
            t["status"] = "done"
            now = _utc_now()
            t["updated_at"] = now
            t["closed_at"] = now
            t["closed_by"] = "qa_verdict"
            t["closure_source"] = "qa_save_validation"
            g_after, per_after = compute_debt_metrics(inbox, base)
            debt_after = per_after.get(ak, {}).get("validation_debt_score")
            if debt_before is not None:
                t["validation_debt_impact"] = {"before": debt_before, "after": debt_after}
            n += 1
    if n:
        save_inbox(base, inbox)
    return n


def update_task_status(
    base: Optional[Path],
    task_id: str,
    status: str,
    assigned_to: Optional[str] = None,
    dismiss_reason: Optional[str] = None,
    closed_by: Optional[str] = None,
    closure_source: Optional[str] = None,
) -> Tuple[bool, str]:
    allowed = {"pending", "done", "dismissed"}
    if status not in allowed:
        return False, f"status debe ser uno de {allowed}"
    inbox = load_inbox(base)
    found = False
    for t in inbox.get("tasks") or []:
        if t.get("task_id") != task_id:
            continue
        found = True
        ak = t.get("area_key") or "_global"
        debt_before = None
        if status in ("done", "dismissed"):
            g_before, per_before = compute_debt_metrics(inbox, base)
            debt_before = per_before.get(ak, {}).get("validation_debt_score")
        t["status"] = status
        now = _utc_now()
        t["updated_at"] = now
        if status in ("done", "dismissed"):
            t["closed_at"] = now
            t["closed_by"] = (closed_by or "").strip() or "operator"
            t["closure_source"] = (closure_source or "").strip() or "dojo_inbox_api"
        if assigned_to is not None:
            t["assigned_to"] = assigned_to
        if dismiss_reason is not None and status == "dismissed":
            t["dismiss_reason"] = (dismiss_reason or "").strip()
        if status in ("done", "dismissed") and debt_before is not None:
            g_after, per_after = compute_debt_metrics(inbox, base)
            debt_after = per_after.get(ak, {}).get("validation_debt_score")
            t["validation_debt_impact"] = {"before": debt_before, "after": debt_after}
        break
    if not found:
        return False, "task_id no encontrado"
    save_inbox(base, inbox)
    return True, "ok"


def build_dojo_candidate_linkage(
    area_key: str,
    rel_obs: List[dict],
    matched_rule_ids: List[str],
    rules_by_id: Dict[str, dict],
    engine_integrated_rule_ids: Optional[set] = None,
    *,
    engine_rule_ids_expected: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Vínculos estables entre candidato Dojo, inbox (task_id determinista) y reglas.
    Los task_id deben coincidir con sync_validation_inbox / _generate_tasks_from_*.
    decision_review solo para reglas PRO esperadas en el área pero no integradas (como en inbox).
    """
    linked_task_ids: List[str] = []
    seen: set = set()

    def add_tid(tid: str) -> None:
        if tid and tid not in seen:
            seen.add(tid)
            linked_task_ids.append(tid)

    eng = engine_integrated_rule_ids or set()

    for o in rel_obs:
        oid = (o.get("observed_id") or "").strip()
        if oid:
            add_tid(_tid("ref", area_key, oid))

    primary_hypothesis_id: Optional[str] = None
    primary_rule_id: Optional[str] = None

    for rid in matched_rule_ids:
        r = rules_by_id.get(rid) or {}
        sup = (r.get("support") or "").lower()
        if not primary_rule_id and rid:
            primary_rule_id = rid
        if sup == "hypothetical":
            if not primary_hypothesis_id and rid:
                primary_hypothesis_id = rid
            add_tid(_tid("hyp", area_key, rid))
            if area_key in ("compset", "ota_visibility"):
                applies = " ".join(str(x).lower() for x in (r.get("applies_to") or []))
                if "compset" in applies or "ota" in applies or "proxy" in applies:
                    add_tid(_tid("cmp", area_key, rid))
        elif sup == "partial":
            add_tid(_tid("rule", area_key, rid))

    expected = list(engine_rule_ids_expected or [])
    for rid in expected:
        if rid not in eng:
            add_tid(_tid("dec", area_key, rid))

    required_review_type = "human_validation_case"
    if primary_hypothesis_id:
        required_review_type = "hypothesis_review"
    elif linked_task_ids and any((o.get("observed_id") or "").strip() for o in rel_obs):
        required_review_type = "refresh_observation_ack"

    close_condition = (
        "Validar el candidato en Dojo (estado dojo_validation_status=validated) y cerrar en inbox "
        "las tareas listadas en linked_task_ids (Hecho) o justificar descarte."
    )

    return {
        "linked_task_ids": linked_task_ids,
        "linked_hypothesis_id": primary_hypothesis_id,
        "linked_rule_id": primary_rule_id,
        "required_review_type": required_review_type,
        "close_condition": close_condition,
    }


def build_inbox_payload(base: Optional[Path] = None) -> Dict[str, Any]:
    """Para API: inbox + métricas."""
    base = base or ROOT
    inbox = load_inbox(base)
    g, per_area = compute_debt_metrics(inbox, base)
    blocked_areas = [
        {
            "area_key": ak,
            "validation_debt_score": b.get("validation_debt_score"),
            "required_pending_count": b.get("required_pending_count"),
        }
        for ak, b in per_area.items()
        if b.get("area_blocked_by_validation")
    ]
    return {
        "inbox": inbox,
        "global_metrics": g,
        "per_area_metrics": per_area,
        "blocked_areas": blocked_areas,
    }
