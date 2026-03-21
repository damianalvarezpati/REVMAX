"""
RevMax — Daily / Nightly Knowledge Refresh
===========================================
Prioriza áreas débiles (Knowledge Inputs), consulta fuentes locales controladas,
registra observed_new_data (nunca auto-aceptado), opcional HTTP allowlist,
genera candidatos Dojo, recalcula scores y escribe trazabilidad estricta.

Artefactos:
  data/knowledge/refresh/knowledge_refresh_runs.jsonl
  data/knowledge/refresh/latest_refresh_summary.json
  data/knowledge/refresh/knowledge_area_adjustments.json
  data/knowledge/refresh/observed_queue.jsonl        (cola para promoción manual)
  data/knowledge/refresh/accepted_knowledge.jsonl    (solo vía accept-observed API)
  data/knowledge/refresh/refresh_funnel_metrics.json   (acumulado funnel + última corrida)
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
REFRESH_DIR = ROOT / "data" / "knowledge" / "refresh"
RUNS_JSONL = REFRESH_DIR / "knowledge_refresh_runs.jsonl"
OBSERVED_QUEUE = REFRESH_DIR / "observed_queue.jsonl"
ACCEPTED_JSONL = REFRESH_DIR / "accepted_knowledge.jsonl"
LATEST_SUMMARY = REFRESH_DIR / "latest_refresh_summary.json"
ADJUSTMENTS_JSON = REFRESH_DIR / "knowledge_area_adjustments.json"
ACCEPTED_HASHES = REFRESH_DIR / "accepted_hashes.json"
STATE_JSON = REFRESH_DIR / "refresh_state.json"
CONFIG_JSON = REFRESH_DIR / "knowledge_refresh_config.json"
TRAINING_CANDIDATES = ROOT / "data" / "dojo" / "training_candidates"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        f.flush()


def _ensure_dirs() -> None:
    REFRESH_DIR.mkdir(parents=True, exist_ok=True)
    TRAINING_CANDIDATES.mkdir(parents=True, exist_ok=True)


def load_refresh_config(base: Path) -> dict:
    return _load_json(base / "data/knowledge/refresh/knowledge_refresh_config.json") or {}


def load_refresh_state(base: Path) -> dict:
    p = base / "data/knowledge/refresh/refresh_state.json"
    return _load_json(p) or {"known_dataset_paths": {}, "last_global_run_at": None}


def save_refresh_state(base: Path, state: dict) -> None:
    p = base / "data/knowledge/refresh/refresh_state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def prioritize_areas(
    areas: List[dict],
    status_order: List[str],
) -> List[dict]:
    """Orden: status (weak primero) luego area_score ascendente."""
    order_idx = {s: i for i, s in enumerate(status_order)}
    return sorted(
        areas,
        key=lambda a: (
            order_idx.get(a.get("status_label") or "usable", 99),
            float(a.get("area_score") or 0),
        ),
    )


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_content_sha256(path: Path, cap: int = 2_000_000) -> Optional[str]:
    try:
        raw = path.read_bytes()[:cap]
    except OSError:
        return None
    return _sha256_bytes(raw)


def _pattern_observation(
    base: Path,
    area_key: str,
    pattern_files: List[str],
    state: dict,
) -> List[dict]:
    """Cambio real de contenido (hash), no solo mtime — evita ruido por touch/save sin delta."""
    out: List[dict] = []
    kn = base / "data/knowledge"
    ph = state.setdefault("pattern_content_hashes", {})
    for fn in pattern_files:
        p = kn / fn
        if not p.is_file():
            continue
        rel = str(p.relative_to(base))
        h = _file_content_sha256(p)
        if not h:
            continue
        prev = ph.get(rel)
        if prev is None:
            ph[rel] = h
            continue
        if h == prev:
            continue
        ph[rel] = h
        out.append(
            {
                "observed_id": f"obs_pat_{_sha256_text(fn + h)[:12]}",
                "kind": "pattern_file_changed",
                "area_key": area_key,
                "summary": f"Patrón actualizado (contenido): {fn}",
                "ref_path": rel,
                "content_hash": h,
                "status": "observed_only",
            }
        )
    return out


def _http_observation(
    base: Path,
    area_key: str,
    url: str,
) -> Optional[dict]:
    import urllib.error
    import urllib.request

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RevMax-KnowledgeRefresh/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            chunk = resp.read(8192)
        h = _sha256_text(chunk.decode("utf-8", errors="replace"))
        return {
            "observed_id": f"obs_http_{h[:12]}",
            "kind": "http_allowlist_fetch",
            "area_key": area_key,
            "summary": f"Fetch allowlist ({len(chunk)} bytes): {url[:80]}",
            "ref_path": url,
            "content_hash": h,
            "status": "observed_only",
        }
    except (urllib.error.URLError, OSError, ValueError) as e:
        return {
            "observed_id": f"obs_http_err_{_sha256_text(url)[:10]}",
            "kind": "http_fetch_error",
            "area_key": area_key,
            "summary": str(e)[:200],
            "ref_path": url,
            "content_hash": "",
            "status": "observed_only",
        }


def _maybe_run_extract(base: Path, cfg: dict) -> Optional[dict]:
    if not cfg.get("run_extract_script"):
        return None
    rel = cfg.get("extract_script_relative") or "scripts/extract_revmax_knowledge.py"
    script = base / rel
    if not script.is_file():
        return {
            "observed_id": "obs_extract_missing",
            "kind": "extract_script_skipped",
            "area_key": "_global",
            "summary": f"Script no encontrado: {rel}",
            "ref_path": str(script),
            "content_hash": "",
            "status": "observed_only",
        }
    try:
        r = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(base),
            capture_output=True,
            text=True,
            timeout=600,
        )
        ok = r.returncode == 0
        return {
            "observed_id": f"obs_extract_{_sha256_text(r.stdout[:500] + str(ok))[:12]}",
            "kind": "extract_script_run",
            "area_key": "_global",
            "summary": f"extract_revmax_knowledge exit={r.returncode}",
            "ref_path": str(script),
            "content_hash": _sha256_text(r.stdout[:2000] or ""),
            "status": "observed_only",
        }
    except (subprocess.TimeoutExpired, OSError) as e:
        return {
            "observed_id": "obs_extract_err",
            "kind": "extract_script_error",
            "area_key": "_global",
            "summary": str(e)[:200],
            "ref_path": str(script),
            "content_hash": "",
            "status": "observed_only",
        }


def _hypothesis_events_for_area(area_key: str, matched_rule_ids: List[str]) -> List[dict]:
    events: List[dict] = []
    if "EVT-001" in matched_rule_ids and area_key == "events":
        events.append(
            {
                "rule_id": "EVT-001",
                "action": "candidate_reinforcement",
                "requires_human_validation": True,
                "note": "Refresh revisó área events; EVT sigue hipotética — no promover sin validación.",
            }
        )
    return events


def _relevant_observations_for_area(
    observed_all: List[dict],
    area_key: str,
    cfg: dict,
) -> List[dict]:
    kinds = list(
        cfg.get("dojo_relevant_observation_kinds")
        or ["dataset_index_path_new", "pattern_file_changed", "http_allowlist_fetch"]
    )
    kind_set = set(kinds)
    out: List[dict] = []
    for o in observed_all:
        k = o.get("kind")
        if k not in kind_set:
            continue
        if k == "dataset_index_path_new":
            touched = o.get("area_keys_touched") or []
            if area_key in touched:
                out.append(o)
        elif k in ("pattern_file_changed", "http_allowlist_fetch", "http_fetch_error"):
            if o.get("area_key") == area_key:
                out.append(o)
    return out


def _count_validated_refresh_dojo_candidates(base: Path) -> int:
    d = base / "data/dojo/training_candidates"
    if not d.is_dir():
        return 0
    n = 0
    for path in d.glob("*.json"):
        data = _load_json(path)
        if not data or data.get("source") != "knowledge_refresh":
            continue
        if (data.get("dojo_validation_status") or "").lower() == "validated":
            n += 1
    return n


def _update_funnel_after_run(base: Path, run_record: dict) -> dict:
    """Acumula métricas de funnel y devuelve bloque para latest_refresh_summary."""
    funnel_path = base / "data/knowledge/refresh/refresh_funnel_metrics.json"
    prev = _load_json(funnel_path) or {"version": 2, "lifetime": {}}
    if not isinstance(prev, dict):
        prev = {"version": 2, "lifetime": {}}
    lt = prev.setdefault("lifetime", {})
    observed = len(run_record.get("observed_new_data") or [])
    dojo_n = len(run_record.get("dojo_cases_generated") or [])
    lt["runs_total"] = int(lt.get("runs_total") or 0) + 1
    lt["observed_total"] = int(lt.get("observed_total") or 0) + observed
    lt["dojo_candidates_generated_total"] = int(lt.get("dojo_candidates_generated_total") or 0) + dojo_n

    deltas = run_record.get("score_deltas_by_area") or {}
    has_delta = any(
        abs(float((d or {}).get("delta_area_score") or 0)) > 1e-6 for d in deltas.values() if isinstance(d, dict)
    )
    if has_delta:
        lt["runs_with_delta_count"] = int(lt.get("runs_with_delta_count") or 0) + 1

    area_changes = sum(
        1
        for d in deltas.values()
        if isinstance(d, dict) and abs(float(d.get("delta_area_score") or 0)) > 1e-6
    )
    lt["area_score_changes_count"] = int(lt.get("area_score_changes_count") or 0) + area_changes

    meaningful = observed > 0 or dojo_n > 0
    if meaningful:
        lt["runs_with_meaningful_output"] = int(lt.get("runs_with_meaningful_output") or 0) + 1

    validated_n = _count_validated_refresh_dojo_candidates(base)
    lt["dojo_candidates_validated"] = validated_n

    acc = int(lt.get("accepted_total") or 0)
    obs_tot = max(int(lt.get("observed_total") or 0), 1)
    lt["acceptance_rate"] = round(acc / obs_tot, 6)

    prev["lifetime"] = lt
    prev["last_run"] = {
        "run_id": run_record.get("run_id"),
        "finished_at": run_record.get("finished_at"),
        "observed_count": observed,
        "dojo_candidates_generated": dojo_n,
        "runs_with_meaningful_output": 1 if meaningful else 0,
        "area_score_changes_count": area_changes,
        "has_score_delta": has_delta,
    }
    prev["last_updated"] = run_record.get("finished_at")
    funnel_path.parent.mkdir(parents=True, exist_ok=True)
    funnel_path.write_text(json.dumps(prev, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "this_run": {
            "observed_count": observed,
            "accepted_count": 0,
            "dojo_candidates_generated": dojo_n,
            "dojo_candidates_validated": validated_n,
            "runs_with_meaningful_output": 1 if meaningful else 0,
            "runs_with_delta": 1 if has_delta else 0,
            "area_score_changes_count": area_changes,
            "acceptance_rate": lt.get("acceptance_rate"),
        },
        "lifetime": dict(lt),
    }


def _increment_funnel_accepted(base: Path) -> None:
    funnel_path = base / "data/knowledge/refresh/refresh_funnel_metrics.json"
    prev = _load_json(funnel_path) or {"version": 2, "lifetime": {}}
    lt = prev.setdefault("lifetime", {})
    lt["accepted_total"] = int(lt.get("accepted_total") or 0) + 1
    obs_tot = max(int(lt.get("observed_total") or 0), 1)
    lt["acceptance_rate"] = round(int(lt["accepted_total"]) / obs_tot, 6)
    prev["last_updated"] = _utc_now()
    funnel_path.parent.mkdir(parents=True, exist_ok=True)
    funnel_path.write_text(json.dumps(prev, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_dojo_candidate(
    base: Path,
    run_id: str,
    area_key: str,
    area_name: str,
    observed_summaries: List[str],
    seq: int,
) -> str:
    fn = f"{run_id[:8]}_{area_key}_{seq}.json"
    p = base / "data/dojo/training_candidates" / fn
    case = {
        "source": "knowledge_refresh",
        "run_id": run_id,
        "area_key": area_key,
        "area_name": area_name,
        "dojo_validation_status": "pending",
        "generated_at": _utc_now(),
        "pending_human_review": True,
        "hotel_name": f"[Refresh] {area_name}",
        "city": "",
        "timestamp": _utc_now(),
        "consolidated_action": "hold",
        "confidence_pct": None,
        "executive_summary": (
            "Candidato generado por Knowledge Refresh. Revisar señales del área y mapeo a pipeline antes de usar como caso gold."
        ),
        "refresh_context": {
            "observed_summaries": observed_summaries[:5],
        },
        "evidence_found": {},
        "analysis_quality": {},
    }
    p.write_text(json.dumps(case, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p.relative_to(base))


def _update_adjustments_file(base: Path, run_record: dict) -> None:
    adj_path = base / "data/knowledge/refresh/knowledge_area_adjustments.json"
    prev = _load_json(adj_path) if adj_path.is_file() else {"version": 1, "by_area": {}}
    by_area = prev.setdefault("by_area", {})
    deltas = run_record.get("score_deltas_by_area") or {}
    for ak, d in deltas.items():
        by_area.setdefault(ak, []).append(
            {
                "run_id": run_record["run_id"],
                "finished_at": run_record["finished_at"],
                "delta_area_score": d.get("delta_area_score"),
                "before": d.get("before"),
                "after": d.get("after"),
            }
        )
        by_area[ak] = by_area[ak][-30:]
    prev["last_updated"] = run_record["finished_at"]
    adj_path.parent.mkdir(parents=True, exist_ok=True)
    adj_path.write_text(json.dumps(prev, indent=2, ensure_ascii=False), encoding="utf-8")


def _area_scores_index(areas: List[dict]) -> Dict[str, dict]:
    return {
        a["area_key"]: {
            "area_score": a.get("area_score"),
            "coverage_score": a.get("coverage_score"),
            "quality_score": a.get("quality_score"),
            "validation_score": a.get("validation_score"),
            "model_readiness_score": a.get("model_readiness_score"),
            "status_label": a.get("status_label"),
        }
        for a in areas
    }


def run_knowledge_refresh(
    base_dir: Optional[Path] = None,
    *,
    mode: str = "manual",
    area_keys: Optional[List[str]] = None,
    write_artifacts: bool = True,
) -> Dict[str, Any]:
    """
    Ejecuta un ciclo de refresh.

    mode: scheduled | manual | area
    area_keys: si se pasa, solo esas áreas (y en orden dado), sin priorización global.
    """
    from knowledge_inputs import compute_knowledge_inputs

    base = base_dir or ROOT
    _ensure_dirs()
    cfg = load_refresh_config(base)
    state = load_refresh_state(base)

    run_id = str(uuid.uuid4())
    started = _utc_now()

    # Primera ejecución: indexar paths actuales sin inundar observed_queue
    if not state.get("bootstrapped"):
        m0 = _load_json(base / "data/datasets/MASTER_DATASET_INDEX.json")
        kmap = state.setdefault("known_dataset_paths", {})
        for ds in (m0 or {}).get("datasets") or []:
            pth = ds.get("path")
            if pth:
                kmap[pth] = {"first_seen_run": "bootstrap", "at": started}
        state["bootstrapped"] = True
        save_refresh_state(base, state)

    before = compute_knowledge_inputs(base_dir=base, write_snapshot=False)
    if before.get("error"):
        return {"ok": False, "error": before["error"], "run_id": run_id}

    areas_before = before.get("areas") or []
    idx_before = _area_scores_index(areas_before)

    kn_cfg = _load_json(base / "data/knowledge/knowledge_areas_config.json") or {}
    area_specs = {s["area_key"]: s for s in kn_cfg.get("areas") or []}

    kb_refresh = cfg.get("knowledge_balancing") or {}
    balance_selection: Dict[str, Any] = {}

    if area_keys:
        to_process = [k for k in area_keys if k in area_specs]
        mode = "area"
        balance_selection = {"policy": "explicit_area_keys", "selected": to_process}
    else:
        cap = int(cfg.get("max_areas_per_run") or 4)
        use_dyn = kb_refresh.get("use_dynamic_area_selection", True) and kb_refresh.get("enabled", True)
        if use_dyn:
            from knowledge_balancing_engine import select_areas_for_refresh

            to_process, balance_selection = select_areas_for_refresh(
                list(areas_before),
                cap,
                prefer_balance=True,
            )
        else:
            ordered = prioritize_areas(
                list(areas_before),
                cfg.get("priority_status_order") or ["weak", "developing", "usable", "strong"],
            )
            to_process = [a["area_key"] for a in ordered[:cap]]
            balance_selection = {"policy": "legacy_status_priority", "selected": to_process}

    sources_consulted: List[dict] = []
    observed_all: List[dict] = []
    accepted_all: List[dict] = []
    dojo_paths: List[str] = []
    hypothesis_events: List[dict] = []
    new_known_paths: List[str] = []

    global_extract = _maybe_run_extract(base, cfg)
    if global_extract:
        observed_all.append(global_extract)
        sources_consulted.append(
            {"type": "extract_script", "target": cfg.get("extract_script_relative"), "status": "run"}
        )

    max_http = 1 if cfg.get("allow_http_fetch") else 0
    http_used = 0

    from knowledge_inputs import _count_datasets_for_area

    master = _load_json(base / "data/datasets/MASTER_DATASET_INDEX.json")
    ds_list = (master or {}).get("datasets") or []
    known = state.setdefault("known_dataset_paths", {})
    sources_consulted.append({"type": "master_dataset_index_scan", "status": "ok", "datasets_total": len(ds_list)})

    all_area_keys = [ak for ak in area_specs.keys()]
    for ds in ds_list:
        path = ds.get("path") or ""
        if not path or path in known:
            continue
        matched_aks = [
            ak for ak in all_area_keys if ak in area_specs and _count_datasets_for_area([ds], area_specs[ak])[0] > 0
        ]
        if not matched_aks:
            continue
        oid = f"obs_ds_{_sha256_text(path)[:12]}"
        observed_all.append(
            {
                "observed_id": oid,
                "kind": "dataset_index_path_new",
                "area_keys_touched": matched_aks,
                "summary": f"Path nuevo en MASTER_DATASET_INDEX: {ds.get('name') or path}",
                "ref_path": path,
                "content_hash": _sha256_text(path + str(ds.get("rows") or "")),
                "status": "observed_only",
            }
        )
        new_known_paths.append(path)

    new_known_paths = list(dict.fromkeys(new_known_paths))

    for ak in to_process:
        spec = area_specs[ak]
        matched_ids = []
        for a in areas_before:
            if a.get("area_key") == ak:
                matched_ids = a.get("rule_ids_in_area") or []
                break

        obs_p = _pattern_observation(base, ak, spec.get("pattern_files") or [], state)
        observed_all.extend(obs_p)
        if spec.get("pattern_files"):
            sources_consulted.append({"area_key": ak, "type": "pattern_files_stat", "status": "ok"})

        if cfg.get("allow_http_fetch") and http_used < max_http:
            allow = cfg.get("http_allowlist") or []
            for u in allow:
                if http_used >= max_http:
                    break
                obs_h = _http_observation(base, ak, u)
                if obs_h:
                    observed_all.append(obs_h)
                    sources_consulted.append({"area_key": ak, "type": "http", "target": u, "status": "ok"})
                    http_used += 1

        hypothesis_events.extend(_hypothesis_events_for_area(ak, matched_ids))

        rel_obs = _relevant_observations_for_area(observed_all, ak, cfg)
        min_rel = int(cfg.get("dojo_min_relevant_observations") or 1)
        if len(rel_obs) < min_rel:
            continue

        from knowledge_balancing_engine import dojo_candidate_multiplier_for_area

        n_base = int(cfg.get("dojo_candidates_per_area") or 1)
        area_row = next((x for x in areas_before if x.get("area_key") == ak), {})
        mult = dojo_candidate_multiplier_for_area(area_row, kb_refresh, len(areas_before))
        n_cand = max(1, min(5, int(round(n_base * mult))))
        summaries = [o["summary"] for o in rel_obs][:5]

        for j in range(n_cand):
            dojo_paths.append(
                _write_dojo_candidate(
                    base,
                    run_id,
                    ak,
                    spec.get("area_name") or ak,
                    summaries,
                    j,
                )
            )

    # Register known paths after successful observations
    for pth in new_known_paths:
        state["known_dataset_paths"][pth] = {"first_seen_run": run_id, "at": started}
    state["last_global_run_at"] = started
    if write_artifacts:
        save_refresh_state(base, state)

    after = compute_knowledge_inputs(base_dir=base, write_snapshot=write_artifacts)
    areas_after = after.get("areas") or []
    idx_after = _area_scores_index(areas_after)

    score_deltas: Dict[str, dict] = {}
    for ak in set(idx_before) | set(idx_after):
        b = idx_before.get(ak, {})
        a = idx_after.get(ak, {})
        score_deltas[ak] = {
            "before": b.get("area_score"),
            "after": a.get("area_score"),
            "delta_area_score": (a.get("area_score") or 0) - (b.get("area_score") or 0)
            if a.get("area_score") is not None and b.get("area_score") is not None
            else None,
        }

    finished = _utc_now()
    run_record = {
        "run_id": run_id,
        "mode": mode,
        "started_at": started,
        "finished_at": finished,
        "areas_prioritized": to_process,
        "areas_reviewed": to_process,
        "sources_consulted": sources_consulted,
        "observed_new_data": observed_all,
        "accepted_knowledge": accepted_all,
        "dojo_cases_generated": [{"path": p} for p in dojo_paths],
        "hypothesis_events": hypothesis_events,
        "scores_before_by_area": idx_before,
        "scores_after_by_area": idx_after,
        "score_deltas_by_area": score_deltas,
        "notes": [
            "accepted_knowledge vacío en ejecución automática — usar POST accept-observed con campos de trazabilidad.",
            f"Observaciones registradas: {len(observed_all)}; candidatos Dojo (solo si relevancia mínima por área): {len(dojo_paths)}.",
        ],
        "knowledge_balancing_selection": balance_selection,
    }

    funnel_block = _update_funnel_after_run(base, run_record)
    run_record["funnel"] = funnel_block

    for ob in observed_all:
        _append_jsonl(base / "data/knowledge/refresh/observed_queue.jsonl", {**ob, "run_id": run_id, "ts": finished})

    if write_artifacts:
        _append_jsonl(base / "data/knowledge/refresh/knowledge_refresh_runs.jsonl", run_record)
        lt = funnel_block.get("lifetime") or {}
        tr = funnel_block.get("this_run") or {}
        summary_public = {
            "run_id": run_id,
            "mode": mode,
            "finished_at": finished,
            "areas_reviewed": to_process,
            "observed_count": len(observed_all),
            "accepted_count": int(lt.get("accepted_total") or 0),
            "dojo_candidates_created": len(dojo_paths),
            "score_deltas_by_area": {
                k: v for k, v in score_deltas.items() if k in to_process
            },
            "hypothesis_events_count": len(hypothesis_events),
            "knowledge_balancing_selection": balance_selection,
            "funnel": funnel_block,
            "funnel_metrics": {
                "observed_count_this_run": tr.get("observed_count"),
                "observed_total": int(lt.get("observed_total") or 0),
                "accepted_total": int(lt.get("accepted_total") or 0),
                "acceptance_rate": lt.get("acceptance_rate"),
                "runs_with_delta_count": int(lt.get("runs_with_delta_count") or 0),
                "dojo_candidates_generated_this_run": tr.get("dojo_candidates_generated"),
                "dojo_candidates_validated": tr.get("dojo_candidates_validated"),
                "runs_with_meaningful_output_total": int(lt.get("runs_with_meaningful_output") or 0),
                "area_score_changes_count_total": int(lt.get("area_score_changes_count") or 0),
            },
        }
        (base / "data/knowledge/refresh/latest_refresh_summary.json").write_text(
            json.dumps(summary_public, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        _update_adjustments_file(base, run_record)

    run_record["ok"] = True
    return run_record


def load_refresh_funnel_metrics(base: Optional[Path] = None) -> Optional[dict]:
    b = base or ROOT
    return _load_json(b / "data/knowledge/refresh/refresh_funnel_metrics.json")


def load_latest_refresh_summary(base: Optional[Path] = None) -> Optional[dict]:
    b = base or ROOT
    p = b / "data/knowledge/refresh/latest_refresh_summary.json"
    s = _load_json(p)
    if not s:
        return None
    fm = load_refresh_funnel_metrics(b)
    if fm and isinstance(fm.get("lifetime"), dict):
        s = {**s, "funnel_lifetime": fm["lifetime"], "funnel_file_last_updated": fm.get("last_updated")}
    return s


def _accepted_jsonl_path(base: Path) -> Path:
    return base / "data/knowledge/refresh/accepted_knowledge.jsonl"


def try_accept_observed(base: Path, payload: dict) -> Tuple[bool, str]:
    """
    Promueve observación → accepted_knowledge con trazabilidad explícita (no automático en refresh).

    Campos obligatorios: observed_id, area_key, source_reference, knowledge_type,
    reason_for_acceptance, linked_rule_or_hypothesis, accepted_by, content_hash.
    Opcionales: run_id, accepted_at (ISO; si falta, se asigna ahora).
    """
    cfg = load_refresh_config(base)
    rules = cfg.get("quality_rules_for_acceptance") or {}
    required = [
        "observed_id",
        "area_key",
        "source_reference",
        "knowledge_type",
        "reason_for_acceptance",
        "linked_rule_or_hypothesis",
        "accepted_by",
        "content_hash",
    ]
    for key in required:
        if not str(payload.get(key) or "").strip():
            return False, f"Falta o vacío: {key}"

    observed_id = str(payload["observed_id"]).strip()
    area_key = str(payload["area_key"]).strip()
    source_reference = str(payload["source_reference"]).strip()
    knowledge_type = str(payload["knowledge_type"]).strip()
    reason = str(payload["reason_for_acceptance"]).strip()
    linked = str(payload["linked_rule_or_hypothesis"]).strip()
    accepted_by = str(payload["accepted_by"]).strip()
    content_hash = str(payload["content_hash"]).strip()

    if rules.get("require_area_key") and not area_key:
        return False, "area_key requerido"
    if rules.get("require_content_hash") and not content_hash:
        return False, "content_hash requerido"

    min_reason = int(rules.get("min_reason_for_acceptance_length") or rules.get("min_summary_length") or 12)
    if len(reason) < min_reason:
        return False, "reason_for_acceptance demasiado corto"

    hp = base / "data/knowledge/refresh/accepted_hashes.json"
    hdata = _load_json(hp) or {"version": 1, "hashes": []}
    hashes = set(hdata.get("hashes") or [])
    if content_hash in hashes:
        return False, "duplicado (hash ya aceptado)"

    accepted_at = str(payload.get("accepted_at") or "").strip() or _utc_now()
    run_id = payload.get("run_id")
    trace_id = str(uuid.uuid4())

    line = {
        "acceptance_trace_id": trace_id,
        "accepted_at": accepted_at,
        "observed_id": observed_id,
        "run_id": run_id,
        "area_key": area_key,
        "source_reference": source_reference,
        "knowledge_type": knowledge_type,
        "reason_for_acceptance": reason,
        "linked_rule_or_hypothesis": linked,
        "accepted_by": accepted_by,
        "content_hash": content_hash,
    }
    aj = _accepted_jsonl_path(base)
    aj.parent.mkdir(parents=True, exist_ok=True)
    _append_jsonl(aj, line)
    hashes.add(content_hash)
    hdata["hashes"] = sorted(hashes)
    hp.parent.mkdir(parents=True, exist_ok=True)
    hp.write_text(json.dumps(hdata, indent=2, ensure_ascii=False), encoding="utf-8")
    _increment_funnel_accepted(base)
    return True, "accepted"


if __name__ == "__main__":
    mode = "manual"
    areas: Optional[List[str]] = None
    if len(sys.argv) > 1:
        if sys.argv[1] == "area" and len(sys.argv) > 2:
            mode = "area"
            areas = [x.strip() for x in sys.argv[2].split(",") if x.strip()]
        elif sys.argv[1] in ("manual", "scheduled"):
            mode = sys.argv[1]
    out = run_knowledge_refresh(mode=mode, area_keys=areas, write_artifacts=True)
    print(json.dumps({k: out[k] for k in ("ok", "run_id", "areas_reviewed", "notes") if k in out}, indent=2))
