"""
RevMax — Panel de Administración
==================================
Corre en localhost:8001
Una sola página, sin dependencias externas, sin auth pública.
Solo para el administrador del sistema (tú).

Uso:
  python admin_panel.py
  Abre: http://localhost:8001
"""

from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import json
import os
import sys
import asyncio
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import job_state
import job_runtime
import job_watchdog
import job_recovery
import job_observability
import analysis_runner

# Fuente de verdad operativa: job_state (data/jobs/<job_id>.json).
# analysis_status.json es LEGACY: solo para polling antiguo del dashboard; se escribe por compatibilidad.
app = FastAPI(title="RevMax Admin")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PORTAL  = os.path.join(BASE_DIR, "data", "portal.db")
DB_ALERTS  = os.path.join(BASE_DIR, "data", "alerts.db")
REPORTS_DIR = os.path.join(BASE_DIR, "data", "reports")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


# ─────────────────────────────────────────────────────────
# HELPERS DB
# ─────────────────────────────────────────────────────────

def portal_db():
    if not os.path.exists(DB_PORTAL):
        return None
    conn = sqlite3.connect(DB_PORTAL)
    conn.row_factory = sqlite3.Row
    return conn

def alerts_db():
    if not os.path.exists(DB_ALERTS):
        return None
    conn = sqlite3.connect(DB_ALERTS)
    conn.row_factory = sqlite3.Row
    return conn

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


# ─────────────────────────────────────────────────────────
# MOCK DATA para demo sin DB
# ─────────────────────────────────────────────────────────

def get_clients():
    conn = portal_db()
    if conn:
        rows = conn.execute(
            "SELECT id, name, city, email, plan, active, created_at FROM hotels ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # Demo: usar config.json como cliente único
    cfg = load_config()
    if cfg.get("name"):
        return [{
            "id": 1,
            "name": cfg["name"],
            "city": cfg.get("city", "—"),
            "email": cfg.get("report_recipient") or cfg.get("smtp_email", "—"),
            "plan": cfg.get("plan", "pro"),
            "active": 1,
            "created_at": datetime.now().strftime("%Y-%m-%d"),
        }]
    return []


def get_reports(hotel_id=None, limit=50):
    conn = portal_db()
    if conn:
        q = "SELECT * FROM reports ORDER BY created_at DESC LIMIT ?"
        args = [limit]
        if hotel_id:
            q = "SELECT * FROM reports WHERE hotel_id = ? ORDER BY created_at DESC LIMIT ?"
            args = [hotel_id, limit]
        rows = conn.execute(q, args).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # Demo: buscar archivos HTML en data/reports/
    reports = []
    if os.path.exists(REPORTS_DIR):
        for f in sorted(os.listdir(REPORTS_DIR), reverse=True)[:limit]:
            if f.endswith(".html"):
                path = os.path.join(REPORTS_DIR, f)
                stat = os.stat(path)
                reports.append({
                    "id": len(reports) + 1,
                    "hotel_id": 1,
                    "date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
                    "status": "done",
                    "overall": "stable",
                    "subject": f.replace(".html", "").replace("_", " "),
                    "html_path": path,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })

    # También buscar en data/
    for fname in ["report_preview.html", "alert_latest.html", "alert_preview.html"]:
        fpath = os.path.join(BASE_DIR, "data", fname)
        if os.path.exists(fpath):
            stat = os.stat(fpath)
            reports.append({
                "id": len(reports) + 1,
                "hotel_id": 1,
                "date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
                "status": "done",
                "overall": "stable",
                "subject": fname.replace(".html", "").replace("_", " "),
                "html_path": fpath,
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

    return reports


def get_alerts_log(limit=100):
    conn = alerts_db()
    if conn:
        rows = conn.execute(
            "SELECT * FROM alerts_log ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    return []


def get_stats():
    clients = get_clients()
    reports = get_reports(limit=200)
    alerts  = get_alerts_log(limit=200)
    today   = datetime.now().strftime("%Y-%m-%d")

    return {
        "total_clients":       len(clients),
        "active_clients":      sum(1 for c in clients if c.get("active")),
        "total_reports":       len(reports),
        "reports_today":       sum(1 for r in reports if r.get("date") == today or r.get("created_at","").startswith(today)),
        "total_alerts":        len(alerts),
        "alerts_today":        sum(1 for a in alerts if a.get("created_at","").startswith(today)),
        "plans": {
            "basic":   sum(1 for c in clients if c.get("plan") == "basic"),
            "pro":     sum(1 for c in clients if c.get("plan") == "pro"),
            "premium": sum(1 for c in clients if c.get("plan") == "premium"),
        }
    }


# ─────────────────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────────────────

@app.get("/api/stats")
def api_stats():
    return get_stats()

@app.get("/api/clients")
def api_clients():
    return get_clients()

@app.get("/api/reports")
def api_reports(hotel_id: int = None, limit: int = 50):
    return get_reports(hotel_id, limit)

@app.get("/api/alerts")
def api_alerts(limit: int = 100):
    return get_alerts_log(limit)

@app.get("/api/report-html/{report_id}")
def api_report_html(report_id: int):
    reports = get_reports(limit=200)
    for r in reports:
        if r.get("id") == report_id and r.get("html_path"):
            path = r["html_path"]
            if not os.path.isabs(path):
                path = os.path.normpath(os.path.join(BASE_DIR, path))
            if os.path.exists(path) and os.path.isfile(path):
                return FileResponse(path, media_type="text/html")
    return JSONResponse({"error": "No encontrado"}, status_code=404)

@app.api_route("/api/preview/{filename}", methods=["GET", "HEAD"])
def api_preview(filename: str, request: Request):
    """Sirve archivos de data/ por nombre (compatibilidad: report_preview.html, etc.)."""
    safe = filename.replace("..", "").replace("/", "")
    path = os.path.join(BASE_DIR, "data", safe)
    if os.path.exists(path) and os.path.isfile(path):
        if request.method == "HEAD":
            return Response(status_code=200, headers={"Content-Type": "text/html"})
        return FileResponse(path, media_type="text/html")
    return JSONResponse({"error": "No encontrado"}, status_code=404)


@app.get("/api/preview/job/{job_id}")
def api_preview_job(job_id: str):
    """Sirve el preview del informe por job_id (data/previews/<job_id>.html). Si no existe, devuelve HTML legible para que el iframe muestre algo."""
    safe_id = job_id.replace("..", "").replace("/", "").strip()
    if not safe_id or len(safe_id) > 64:
        return JSONResponse({"error": "job_id inválido"}, status_code=400)
    path = os.path.join(BASE_DIR, "data", "previews", f"{safe_id}.html")
    if os.path.exists(path) and os.path.isfile(path):
        return FileResponse(path, media_type="text/html")
    # Si no hay archivo, devolver 200 con HTML para que el iframe muestre mensaje (no 404 en blanco)
    fallback_html = (
        "<!DOCTYPE html><html lang='es'><head><meta charset='UTF-8'><title>RevMax</title></head><body style='margin:24px;font-family:sans-serif;'>"
        "<p style='color:#712B13;'>Preview no encontrado.</p>"
        "<p>Job: " + safe_id + ". El informe puede estar generándose o hubo un error al guardar.</p>"
        "</body></html>"
    )
    return Response(content=fallback_html, media_type="text/html")

@app.post("/api/add-client")
async def api_add_client(request: Request):
    data = await request.json()
    cfg = load_config()

    # Guardar como config.json si no hay DB
    conn = portal_db()
    if conn:
        token = __import__('secrets').token_urlsafe(32)
        pw = __import__('hashlib').sha256(data.get("password","revmax").encode()).hexdigest()
        conn.execute(
            "INSERT OR IGNORE INTO hotels (name,city,email,password,token,plan) VALUES (?,?,?,?,?,?)",
            (data["name"], data["city"], data["email"], pw, token, data.get("plan","pro"))
        )
        conn.commit()
        hotel_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        cfg_client = {**cfg, "name": data["name"], "city": data["city"],
                      "report_recipient": data["email"], "plan": data.get("plan","pro")}
        conn.execute(
            "UPDATE hotels SET config=? WHERE id=?",
            (json.dumps(cfg_client), hotel_id)
        )
        conn.commit()
        conn.close()
    else:
        cfg.update({"name": data["name"], "city": data["city"],
                    "report_recipient": data["email"], "plan": data.get("plan","pro")})
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)

    return {"ok": True, "message": f"Cliente '{data['name']}' añadido"}


@app.post("/api/run-analysis")
async def api_run_analysis(request: Request):
    data = await request.json()
    hotel_name = data.get("hotel_name", "")
    hotel_id   = data.get("hotel_id", 1)

    cfg = load_config()
    api_key = cfg.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY","")
    city    = data.get("city") or cfg.get("city","")

    if not api_key:
        return JSONResponse({"error": "Falta ANTHROPIC_API_KEY en config.json"}, status_code=400)
    if not hotel_name:
        return JSONResponse({"error": "Falta nombre del hotel"}, status_code=400)

    active_job_id = job_state.has_active_job_for_hotel(BASE_DIR, hotel_name)
    if active_job_id is not None:
        return JSONResponse(
            {"error": "Ya hay un análisis en curso para este hotel.", "active_job_id": active_job_id},
            status_code=409,
        )

    send_email = data.get("send_email", False)
    fast_demo = data.get("fast_demo", False)
    job_id = job_state.create_job(BASE_DIR, hotel_name, city, hotel_id=hotel_id, fast_demo=fast_demo)
    _write_analysis_status("running")

    task = asyncio.create_task(_run_bg(job_id, hotel_name, city, api_key, hotel_id, cfg, send_email, fast_demo))
    await job_runtime.register(job_id, task)
    msg = "Demo rápido iniciado (~20 s)" if fast_demo else f"Análisis iniciado para '{hotel_name}' (1–2 min)"
    print(f"[RevMax] run-analysis launched job_id={job_id} hotel={hotel_name!r} fast_demo={fast_demo}", flush=True)
    return {"ok": True, "job_id": job_id, "message": msg}


@app.get("/api/job-status/{job_id}")
def api_job_status(job_id: str):
    """Devuelve el estado persistente del job y meta (timing, calidad, evidencias, pasos). 404 si no existe. Siempre incluye progress_steps (9 pasos)."""
    job = job_state.get_job(BASE_DIR, job_id)
    if job is None:
        return JSONResponse({"error": "Job no encontrado", "job_id": job_id}, status_code=404)
    meta = analysis_runner.read_job_meta(BASE_DIR, job_id)
    progress_steps = None
    if meta:
        progress_steps = meta.get("progress_steps")
    if progress_steps is None:
        progress_steps = analysis_runner.read_job_progress(BASE_DIR, job_id)
    if not progress_steps or len(progress_steps) != 9:
        progress_steps = analysis_runner.build_fallback_progress_steps(
            job.get("stage") or "starting",
            job.get("status") or "pending",
            job.get("progress_pct") or 0,
        )
    out = dict(job)
    out["progress_steps"] = progress_steps
    if meta:
        out["analysis_timing"] = meta.get("analysis_timing")
        out["analysis_quality"] = meta.get("analysis_quality")
        out["evidence_found"] = meta.get("evidence_found")
        out["result_summary"] = meta.get("result_summary")
    return out


@app.get("/api/jobs")
def api_list_jobs(limit: int = 50):
    """Lista los jobs más recientes (por updated_at). Útil para el dashboard."""
    jobs = job_state.list_recent_jobs(BASE_DIR, limit=min(limit, 100))
    return {"jobs": jobs}


DEFAULT_STALE_SECONDS = 900


@app.post("/api/jobs/run-watchdog")
def api_run_watchdog(
    max_idle_seconds: float = DEFAULT_STALE_SECONDS,
    dry_run: bool = False,
):
    """
    Marca como stalled los jobs activos sin actualización en max_idle_seconds.
    No marca stalled si el task sigue vivo en runtime (reconciliación).
    dry_run=true: solo devuelve resumen, no escribe.
    """
    result = job_watchdog.mark_stale_jobs(
        BASE_DIR,
        max_idle_seconds,
        stalled_message=f"Job colgado: sin actualización en {int(max_idle_seconds)} s.",
        is_alive=job_runtime.is_running,
        dry_run=dry_run,
    )
    return {
        "reviewed": result["reviewed"],
        "active_count": result["active_count"],
        "alive_in_runtime": result["alive_in_runtime"],
        "marked_stalled": result["marked_stalled"],
        "marked_stalled_ids": result.get("marked_stalled_ids", []),
        "ignored": result["ignored"],
        "dry_run": result.get("dry_run", False),
    }


@app.get("/api/jobs/runtime")
def api_jobs_runtime():
    """
    Observabilidad: snapshot de runtime vs persistencia para diagnóstico.
    Incluye job_ids activos en runtime, orphaned, mismatch y conteos por estado.
    """
    return job_observability.get_runtime_snapshot(
        BASE_DIR,
        get_active_job_ids_fn=job_runtime.get_active_job_ids,
        is_running_fn=job_runtime.is_running,
    )


@app.post("/api/jobs/{job_id}/cancel")
def api_cancel_job(job_id: str):
    """
    Cancela un job activo. Si hay task viva, la cancela; el job queda en estado terminal (cancelled).
    Si el job no está activo, devuelve 400 con mensaje claro.
    """
    job = job_state.get_job(BASE_DIR, job_id)
    if job is None:
        return JSONResponse(
            {"error": "Job no encontrado", "job_id": job_id},
            status_code=404,
        )
    from job_schema import ACTIVE_STATUSES
    if job.get("status") not in ACTIVE_STATUSES:
        return JSONResponse(
            {
                "error": "El job no está activo; no se puede cancelar.",
                "job_id": job_id,
                "current_status": job.get("status"),
            },
            status_code=400,
        )
    now_iso = datetime.utcnow().isoformat() + "Z"
    job_state.update_job(
        BASE_DIR,
        job_id,
        status="cancelled",
        stage="error",
        error_message="Cancelado por el usuario.",
        completed_at=now_iso,
    )
    cancelled_task = job_runtime.cancel_task(job_id)
    return {
        "ok": True,
        "job_id": job_id,
        "message": "Job cancelado.",
        "task_was_running": cancelled_task,
    }


@app.post("/api/jobs/run-recovery")
def api_run_recovery(dry_run: bool = False, policy: str = "stalled"):
    """
    Ejecuta el saneamiento de startup/crash recovery: jobs activos en persistencia
    sin task viva en runtime se marcan según policy (stalled o failed).
    dry_run=true: solo lista qué jobs se sanearían, sin escribir.
    """
    if policy not in ("stalled", "failed"):
        return JSONResponse(
            {"error": "policy debe ser 'stalled' o 'failed'"},
            status_code=400,
        )
    result = job_recovery.run_startup_recovery(
        BASE_DIR,
        job_runtime.is_running,
        policy=policy,
        dry_run=dry_run,
    )
    return {
        "ok": True,
        "orphaned": [{"job_id": o[0], "hotel_name": o[1], "status_applied": o[2]} for o in result["orphaned"]],
        "dry_run": result["dry_run"],
    }


# ─────────────────────────────────────────────────────────
# LEGACY — analysis_status.json (idle | running | success | error)
# Solo para compatibilidad con polling antiguo del dashboard.
# analysis_runner NO escribe aquí; solo recibe callbacks on_legacy_success / on_legacy_error
# que admin_panel usa para escribir este archivo. Fuente de verdad de jobs: job_state (data/jobs/).
# ─────────────────────────────────────────────────────────

def _analysis_status_path():
    return os.path.join(BASE_DIR, "data", "analysis_status.json")


def _write_analysis_status(status: str, **kwargs):
    """LEGACY: escribe analysis_status.json para polling antiguo."""
    p = _analysis_status_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    try:
        data = {"status": status, "at": datetime.now().isoformat(), **kwargs}
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
    except Exception:
        pass

async def _run_bg(job_id, hotel_name, city, api_key, hotel_id, cfg, send_email=False, fast_demo=False):
    """
    Orquesta la ejecución del análisis delegando en analysis_runner.
    Registra errores en log. Siempre da de baja el task en job_runtime al terminar.
    """
    try:
        await analysis_runner.run_analysis_job(
            base_dir=BASE_DIR,
            job_id=job_id,
            hotel_name=hotel_name,
            city=city,
            api_key=api_key,
            hotel_id=hotel_id,
            cfg=cfg,
            send_email=send_email,
            fast_demo=fast_demo,
            get_db_conn=portal_db,
            on_legacy_success=lambda: _write_analysis_status("success"),
            on_legacy_error=lambda err, src, exc: _write_analysis_status("error", error=err, source=src, exc_type=exc),
        )
    except Exception as e:
        import traceback
        err_log = os.path.join(BASE_DIR, "data", "admin_errors.log")
        os.makedirs(os.path.dirname(err_log), exist_ok=True)
        try:
            with open(err_log, "a", encoding="utf-8") as f:
                f.write(f"\n{datetime.now().isoformat()} ERROR {hotel_name}:\n{traceback.format_exc()}\n")
        except Exception:
            pass
    finally:
        job_runtime.unregister(job_id)


@app.get("/api/analysis-status")
def api_analysis_status():
    """LEGACY: estado único para polling antiguo: { status: idle|running|success|error, at?, error?, source?, exc_type? }."""
    p = _analysis_status_path()
    if not os.path.exists(p):
        return {"status": "idle", "at": None}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"status": "idle", "at": None}


@app.post("/api/update-plan")
async def api_update_plan(request: Request):
    data = await request.json()
    conn = portal_db()
    if conn:
        conn.execute("UPDATE hotels SET plan=? WHERE id=?", (data["plan"], data["hotel_id"]))
        conn.commit(); conn.close()
    return {"ok": True}


@app.post("/api/toggle-client")
async def api_toggle_client(request: Request):
    data = await request.json()
    conn = portal_db()
    if conn:
        conn.execute("UPDATE hotels SET active=? WHERE id=?", (data["active"], data["hotel_id"]))
        conn.commit(); conn.close()
    return {"ok": True}


# ─────────────────────────────────────────────────────────
# FRONTEND — Consola operativa (operator_console/operator_ui.html)
# ─────────────────────────────────────────────────────────

_OPERATOR_UI_PATH = os.path.join(BASE_DIR, "operator_console", "operator_ui.html")


def _load_operator_ui() -> str:
    """Carga el HTML de la consola operativa."""
    if os.path.isfile(_OPERATOR_UI_PATH):
        with open(_OPERATOR_UI_PATH, encoding="utf-8") as f:
            return f.read()
    return "<!DOCTYPE html><html><body><p>operator_ui.html no encontrado.</p></body></html>"




@app.get("/", response_class=HTMLResponse)
def serve_admin():
    return HTMLResponse(_load_operator_ui())


@app.get("/api/config")
def api_get_config():
    return load_config()


# ─────────────────────────────────────────────────────────
# QA LAYER — validación humana e historial
# ─────────────────────────────────────────────────────────

QA_RUNS_DIR = os.path.join(BASE_DIR, "data", "qa_runs")


def _load_qa_cases(limit: int = 100):
    try:
        from qa_registry import load_validation_cases
        return load_validation_cases(base_dir=BASE_DIR, limit=limit)
    except Exception:
        return []


def _build_qa_decision_summary(cases: list):
    try:
        from qa_registry import build_qa_decision_summary
        return build_qa_decision_summary(cases)
    except Exception:
        return {"total_cases": 0, "human_score_mean": None, "human_verdict_pct": None, "most_common_issues": [], "recommended_next_adjustment": None}


@app.get("/api/qa/cases")
def api_qa_cases(limit: int = 100):
    """Lista casos de validación en data/qa_runs/."""
    return {"cases": _load_qa_cases(limit=min(limit, 200))}


@app.get("/api/qa/summary")
def api_qa_summary():
    """Resumen para diagnóstico del modelo: build_qa_decision_summary()."""
    cases = _load_qa_cases(limit=200)
    return _build_qa_decision_summary(cases)


@app.post("/api/qa/save-validation")
async def api_qa_save_validation(request: Request):
    """
    Crea o actualiza un caso de validación a partir del job actual.
    Body: { job_id, score (1-5), verdict (agree|partial|disagree), feedback (str), adjustment_decision (str) }.
    """
    data = await request.json()
    job_id = data.get("job_id")
    score = data.get("score")
    verdict = data.get("verdict")
    feedback = (data.get("feedback") or "").strip()
    adjustment_decision = (data.get("adjustment_decision") or "").strip()
    if not job_id:
        return JSONResponse({"error": "Falta job_id"}, status_code=400)
    if score is not None and (not isinstance(score, int) or not 1 <= score <= 5):
        return JSONResponse({"error": "score debe ser un entero entre 1 y 5"}, status_code=400)
    if verdict is not None and verdict not in ("agree", "partial", "disagree"):
        return JSONResponse({"error": "verdict debe ser agree, partial o disagree"}, status_code=400)

    job = job_state.get_job(BASE_DIR, job_id)
    if job is None:
        return JSONResponse({"error": "Job no encontrado"}, status_code=404)
    meta = analysis_runner.read_job_meta(BASE_DIR, job_id)
    if not meta:
        return JSONResponse({"error": "No hay meta de análisis para este job (¿completado?)"}, status_code=400)

    result_summary = meta.get("result_summary") or {}
    evidence = meta.get("evidence_found") or {}
    quality = meta.get("analysis_quality") or {}
    completed = job.get("completed_at") or datetime.utcnow().isoformat() + "Z"
    ts = completed[:19].replace("T", " ").replace("Z", "") if isinstance(completed, str) else datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    case = {
        "hotel_name": job.get("hotel_name") or "Unknown",
        "city": job.get("city") or "",
        "timestamp": completed,
        "job_id": job_id,
        "consolidated_action": result_summary.get("consolidated_action", "hold"),
        "confidence_pct": result_summary.get("confidence_pct"),
        "executive_summary": result_summary.get("executive_summary", ""),
        "evidence_found": evidence,
        "analysis_quality": quality,
    }
    try:
        from qa_registry import save_validation_case, apply_human_review
        path = save_validation_case(case, base_dir=BASE_DIR)
        updated = apply_human_review(
            path,
            score=score,
            feedback=feedback or None,
            verdict=verdict,
            adjustment_decision=adjustment_decision or None,
        )
        return {"ok": True, "path": path, "case": updated}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/save-config")
async def api_save_config(request: Request):
    data = await request.json()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {"ok": True}


@app.on_event("startup")
def startup_recovery():
    """Al arrancar, sanea jobs activos huérfanos (sin task viva) por crash/reinicio."""
    try:
        result = job_recovery.run_startup_recovery(
            BASE_DIR,
            job_runtime.is_running,
            policy="stalled",
        )
        if result["orphaned"]:
            import logging
            logging.getLogger("revmax").warning(
                "Startup recovery: %d job(s) marcados stalled (sin task viva)",
                len(result["orphaned"]),
            )
    except Exception:
        pass


if __name__ == "__main__":
    import uvicorn
    print("\nRevMax Admin Panel")
    print("==================")
    print("Abre en tu navegador: http://localhost:8001\n")
    uvicorn.run("admin_panel:app", host="127.0.0.1", port=8001, reload=False)
