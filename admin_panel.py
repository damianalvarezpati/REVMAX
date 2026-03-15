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
    return {"ok": True, "job_id": job_id, "message": msg}


@app.get("/api/job-status/{job_id}")
def api_job_status(job_id: str):
    """Devuelve el estado persistente del job y meta (timing, calidad, evidencias, pasos). 404 si no existe."""
    job = job_state.get_job(BASE_DIR, job_id)
    if job is None:
        return JSONResponse({"error": "Job no encontrado", "job_id": job_id}, status_code=404)
    meta = analysis_runner.read_job_meta(BASE_DIR, job_id)
    progress_steps = None
    if meta:
        progress_steps = meta.get("progress_steps")
    if progress_steps is None:
        progress_steps = analysis_runner.read_job_progress(BASE_DIR, job_id)
    out = dict(job)
    if progress_steps is not None:
        out["progress_steps"] = progress_steps
    if meta:
        out["analysis_timing"] = meta.get("analysis_timing")
        out["analysis_quality"] = meta.get("analysis_quality")
        out["evidence_found"] = meta.get("evidence_found")
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
# FRONTEND — PANEL DE ADMIN COMPLETO
# ─────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RevMax Admin</title>
<style>
:root{--bg:#F0EDE6;--s:#fff;--s2:#F5F2EB;--b:#DDD9D0;--b2:#C8C4BB;
--tx:#1D2B1D;--tx2:#5F5E5A;--tx3:#9B9890;
--g:#1D9E75;--gd:#085041;--gb:#E1F5EE;
--a:#BA7517;--ab:#FAEEDA;--r:#D85A30;--rb:#FAECE7;
--bl:#185FA5;--blb:#E6F1FB;--hd:#1D2B1D;--rad:10px;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:var(--bg);color:var(--tx);font-size:14px;}
.layout{display:flex;min-height:100vh;}
.side{width:200px;background:var(--hd);flex-shrink:0;display:flex;
      flex-direction:column;padding:20px 0;position:fixed;top:0;left:0;height:100vh;}
.main{margin-left:200px;padding:28px;flex:1;}
.logo{padding:0 18px 20px;border-bottom:1px solid rgba(255,255,255,.1);}
.logo-t{font-size:17px;font-weight:700;color:#5DCAA5;}
.logo-s{font-size:11px;color:rgba(255,255,255,.35);margin-top:1px;}
.nav{padding:14px 0;flex:1;}
.ni{display:flex;align-items:center;gap:8px;padding:9px 18px;
    color:rgba(255,255,255,.55);cursor:pointer;font-size:13px;
    border-left:2px solid transparent;transition:all .12s;}
.ni:hover{color:#fff;background:rgba(255,255,255,.05);}
.ni.on{color:#5DCAA5;border-left-color:#5DCAA5;background:rgba(93,202,165,.08);}
.ni .ico{width:15px;text-align:center;font-size:13px;}
.badge{margin-left:auto;background:var(--r);color:#fff;
       font-size:10px;padding:1px 6px;border-radius:10px;font-weight:600;}
.side-foot{padding:14px 18px;border-top:1px solid rgba(255,255,255,.08);
           font-size:11px;color:rgba(255,255,255,.35);}
/* metrics */
.mrow{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:22px;}
.mc{background:var(--s2);border-radius:8px;padding:14px;}
.ml{font-size:11px;color:var(--tx3);text-transform:uppercase;letter-spacing:.05em;margin-bottom:5px;}
.mv{font-size:22px;font-weight:700;color:var(--tx);}
.ms{font-size:11px;color:var(--tx3);margin-top:2px;}
.mc.hi .mv{color:var(--g);}
/* page header */
.ph{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:10px;}
.pt{font-size:19px;font-weight:700;}
.ps{font-size:12px;color:var(--tx2);margin-top:1px;}
/* buttons */
.btn{padding:8px 16px;border-radius:8px;font-size:13px;font-weight:500;
     cursor:pointer;border:none;transition:all .12s;display:inline-flex;align-items:center;gap:5px;}
.bp{background:var(--g);color:#fff;}.bp:hover{background:var(--gd);}
.bs{background:var(--s);color:var(--tx);border:1px solid var(--b);}.bs:hover{background:var(--s2);}
.br{background:var(--rb);color:var(--r);border:1px solid #F0997B;}
.btn:disabled{opacity:.45;cursor:not-allowed;}
/* cards */
.card{background:var(--s);border:1px solid var(--b);border-radius:var(--rad);padding:18px;}
.ct{font-size:11px;font-weight:600;color:var(--tx2);text-transform:uppercase;
    letter-spacing:.06em;margin-bottom:14px;}
/* table */
.tbl{width:100%;border-collapse:collapse;font-size:13px;}
.tbl th{padding:8px 12px;text-align:left;font-size:11px;color:var(--tx2);
        font-weight:600;border-bottom:1px solid var(--b);background:var(--s2);}
.tbl td{padding:10px 12px;border-bottom:1px solid var(--b);color:var(--tx);}
.tbl tr:last-child td{border-bottom:none;}
.tbl tr:hover td{background:var(--s2);}
/* badges */
.bpro{background:#EEEDFE;color:#3C3489;border-radius:20px;font-size:10px;
      padding:2px 8px;font-weight:600;}
.bbasic{background:var(--s2);color:var(--tx2);border-radius:20px;font-size:10px;padding:2px 8px;}
.bprem{background:#FBEAF0;color:#72243E;border-radius:20px;font-size:10px;
       padding:2px 8px;font-weight:600;}
.bon{background:var(--gb);color:var(--gd);border-radius:20px;font-size:10px;padding:2px 8px;}
.boff{background:var(--rb);color:var(--r);border-radius:20px;font-size:10px;padding:2px 8px;}
.bhigh{background:var(--rb);color:var(--r);border-radius:20px;font-size:10px;padding:2px 8px;font-weight:600;}
.bmed{background:var(--ab);color:var(--a);border-radius:20px;font-size:10px;padding:2px 8px;}
.blow{background:var(--gb);color:var(--gd);border-radius:20px;font-size:10px;padding:2px 8px;}
.bdone{background:var(--gb);color:var(--gd);border-radius:20px;font-size:10px;padding:2px 8px;}
.berr{background:var(--rb);color:var(--r);border-radius:20px;font-size:10px;padding:2px 8px;}
.brun{background:var(--blb);color:var(--bl);border-radius:20px;font-size:10px;padding:2px 8px;}
/* modal */
.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);
         z-index:200;align-items:center;justify-content:center;}
.overlay.open{display:flex;}
.modal{background:var(--s);border-radius:14px;padding:26px;
       width:92%;max-width:520px;max-height:85vh;overflow-y:auto;}
.mttl{font-size:16px;font-weight:700;margin-bottom:16px;
      display:flex;justify-content:space-between;align-items:center;}
.mclose{cursor:pointer;color:var(--tx3);font-size:20px;line-height:1;}
/* form */
.fg{margin-bottom:14px;}
.fl{display:block;font-size:12px;font-weight:500;color:var(--tx2);margin-bottom:5px;}
.fi{width:100%;padding:9px 12px;border:1px solid var(--b);border-radius:8px;
    font-size:13px;color:var(--tx);background:var(--s);outline:none;}
.fi:focus{border-color:var(--g);}
select.fi{cursor:pointer;}
/* toast */
.toast{position:fixed;bottom:22px;right:22px;padding:11px 18px;border-radius:9px;
       font-size:13px;font-weight:500;z-index:999;display:none;
       background:var(--tx);color:#fff;}
.toast.ok{background:var(--g);}
.toast.err{background:var(--r);}
/* iframe viewer */
.iframe-wrap{border:1px solid var(--b);border-radius:8px;overflow:hidden;margin-top:12px;}
iframe{width:100%;border:none;}
/* log item */
.logitem{display:flex;gap:10px;align-items:flex-start;
         padding:10px 0;border-bottom:1px solid var(--b);}
.logitem:last-child{border-bottom:none;}
.logdot{width:7px;height:7px;border-radius:50%;flex-shrink:0;margin-top:4px;}
.logtxt{font-size:13px;color:var(--tx);flex:1;}
.logdate{font-size:11px;color:var(--tx3);}
/* spinner */
.spin{display:inline-block;width:13px;height:13px;border:2px solid rgba(255,255,255,.3);
      border-top-color:#fff;border-radius:50%;animation:sp .7s linear infinite;}
@keyframes sp{to{transform:rotate(360deg)}}
/* status bar */
.sbar{background:var(--hd);color:rgba(255,255,255,.5);font-size:11px;
      padding:6px 18px;text-align:right;}
</style>
</head>
<body>
<div class="layout">
<nav class="side">
  <div class="logo"><div class="logo-t">RevMax</div><div class="logo-s">Admin Panel</div></div>
  <div class="nav">
    <div class="ni on" onclick="nav('dash')" id="nav-dash"><span class="ico">◈</span>Dashboard</div>
    <div class="ni" onclick="nav('clients')" id="nav-clients"><span class="ico">◉</span>Clientes</div>
    <div class="ni" onclick="nav('reports')" id="nav-reports"><span class="ico">◎</span>Informes</div>
    <div class="ni" onclick="nav('alerts')" id="nav-alerts"><span class="ico">◌</span>Alertas
      <span class="badge" id="ab" style="display:none">0</span></div>
    <div class="ni" onclick="nav('run')" id="nav-run"><span class="ico">▷</span>Pruebas / Envío manual</div>
    <div class="ni" onclick="nav('config')" id="nav-config"><span class="ico">◇</span>Config</div>
  </div>
  <div class="side-foot" id="last-refresh">—</div>
</nav>

<main class="main">

<!-- DASHBOARD -->
<div id="pg-dash">
  <div class="ph"><div><div class="pt">Dashboard</div><div class="ps" id="dash-ts">—</div></div>
    <button class="btn bs" onclick="loadAll()">↺ Refrescar</button></div>
  <div class="card" style="margin-bottom:14px;background:linear-gradient(135deg, var(--blb) 0%, rgba(30,80,120,.15) 100%);border:1px solid rgba(30,120,180,.3);">
    <div class="ct">Pruebas y envío manual</div>
    <p style="color:var(--tx2);font-size:13px;margin:0 0 12px 0;">Los informes a clientes se generan y envían solos (programación diaria). Aquí puedes <strong>probar</strong> el sistema o mandar un <strong>informe extra</strong> cuando quieras.</p>
    <div style="display:flex;gap:10px;flex-wrap:wrap;">
      <button class="btn bp" onclick="nav('run'); document.getElementById('run-mode').value='preview';" style="flex:1;min-width:160px;">◇ Probar (solo preview)</button>
      <button class="btn bp" onclick="nav('run'); document.getElementById('run-mode').value='send';" style="flex:1;min-width:160px;">✉ Enviar informe ahora</button>
    </div>
  </div>
  <div class="mrow" id="mrow"></div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
    <div class="card"><div class="ct">Últimos informes</div>
      <table class="tbl"><tbody id="dash-rep"></tbody></table></div>
    <div class="card"><div class="ct">Últimas alertas</div>
      <div id="dash-alrt"></div></div>
  </div>
</div>

<!-- CLIENTES -->
<div id="pg-clients" style="display:none">
  <div class="ph">
    <div><div class="pt">Clientes</div><div class="ps">Gestión de hoteles suscritos</div></div>
    <button class="btn bp" onclick="openAddClient()">+ Añadir cliente</button>
  </div>
  <div class="card" style="padding:0;overflow:hidden">
    <table class="tbl">
      <thead><tr><th>Hotel</th><th>Ciudad</th><th>Email</th><th>Plan</th>
        <th>Estado</th><th>Creado</th><th>Acciones</th></tr></thead>
      <tbody id="clients-body"></tbody>
    </table>
  </div>
</div>

<!-- INFORMES -->
<div id="pg-reports" style="display:none">
  <div class="ph"><div><div class="pt">Informes</div>
    <div class="ps">Historial de todos los análisis enviados</div></div></div>
  <div class="card" style="padding:0;overflow:hidden">
    <table class="tbl">
      <thead><tr><th>Hotel</th><th>Fecha</th><th>Estado</th>
        <th>Resumen</th><th>Ver</th></tr></thead>
      <tbody id="reports-body"></tbody>
    </table>
  </div>
</div>

<!-- ALERTAS -->
<div id="pg-alerts" style="display:none">
  <div class="ph"><div><div class="pt">Log de alertas</div>
    <div class="ps">Todas las alertas generadas por el motor</div></div></div>
  <div class="card">
    <div id="alerts-body"></div>
  </div>
</div>

<!-- LANZAR ANÁLISIS -->
<div id="pg-run" style="display:none">
  <div class="ph"><div><div class="pt">Pruebas y envío manual</div>
    <div class="ps">Los informes diarios son automáticos. Aquí puedes ejecutar un análisis de prueba (solo preview) o mandar un informe extra por email cuando quieras.</div></div></div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
    <div class="card">
      <div class="ct">Configuración del análisis</div>
      <div class="fg"><label class="fl">Hotel (nombre exacto en Booking)</label>
        <input class="fi" id="run-hotel" placeholder="ej: Hotel Arts Barcelona"></div>
      <div class="fg"><label class="fl">Ciudad</label>
        <input class="fi" id="run-city" placeholder="ej: Barcelona"></div>
      <div class="fg"><label class="fl">Email destinatario (opcional, para enviar)</label>
        <input class="fi" id="run-email" placeholder="director@hotel.com" type="email"></div>
      <div class="fg"><label class="fl">Modo</label>
        <select class="fi" id="run-mode">
          <option value="preview">Solo generar informe (preview, no envía email)</option>
          <option value="send">Generar informe y enviar por email</option>
        </select></div>
      <div class="fg" style="display:flex;align-items:center;gap:8px;">
        <input type="checkbox" id="run-fast-demo" style="width:18px;height:18px;" onchange="toggleDemoWarning()">
        <label class="fl" for="run-fast-demo" style="margin:0;">DEMO RÁPIDA / INFORME DE PRUEBA — sin scraping ni análisis completo (~20 s)</label>
      </div>
      <div id="run-demo-warning" style="display:none;margin-bottom:10px;padding:10px 12px;background:var(--ab);border:1px solid var(--a);border-radius:8px;font-size:12px;color:var(--tx);">
        Este modo no usa scraping ni los 7 agentes. Solo genera un informe de prueba. Para análisis real, desmarca la casilla.
      </div>
      <button class="btn bp" style="width:100%;justify-content:center;margin-top:4px;"
        id="run-btn" onclick="runAnalysis()">
        <span id="run-btn-txt">▷ Generar informe</span>
      </button>
      <div id="run-progress-steps" style="display:none;margin-top:12px;background:var(--s2);border-radius:8px;padding:12px;font-size:12px;"></div>
      <div id="run-status" style="display:none;margin-top:14px;background:var(--blb);
           color:var(--bl);border-radius:8px;padding:12px;font-size:13px;"></div>
      <div id="run-evidence" style="display:none;margin-top:14px;"></div>
      <div id="run-quality" style="display:none;margin-top:14px;"></div>
    </div>
    <div class="card">
      <div class="ct">Vista previa del email</div>
      <div id="preview-area">
        <div style="color:var(--tx3);font-size:13px;padding:20px 0;text-align:center;">
          Ejecuta un análisis para ver la vista previa aquí
        </div>
      </div>
    </div>
  </div>
</div>

<!-- CONFIG -->
<div id="pg-config" style="display:none">
  <div class="ph"><div><div class="pt">Configuración del sistema</div></div>
    <button class="btn bp" onclick="saveConfig()">Guardar</button></div>
  <div style="display:flex;flex-direction:column;gap:14px;">
    <div class="card">
      <div class="ct">Hotel principal (config.json)</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div class="fg"><label class="fl">Nombre del hotel</label>
          <input class="fi" id="c-name"></div>
        <div class="fg"><label class="fl">Ciudad</label>
          <input class="fi" id="c-city"></div>
      </div>
    </div>
    <div class="card">
      <div class="ct">API y email</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div class="fg"><label class="fl">Anthropic API Key</label>
          <input class="fi" id="c-apikey" type="password" placeholder="sk-ant-..."></div>
        <div class="fg"><label class="fl">Email SMTP (Gmail)</label>
          <input class="fi" id="c-smtp"></div>
        <div class="fg"><label class="fl">Contraseña aplicación Gmail</label>
          <input class="fi" id="c-smtppass" type="password"></div>
        <div class="fg"><label class="fl">Destinatario informes</label>
          <input class="fi" id="c-recipient"></div>
      </div>
    </div>
    <div class="card">
      <div class="ct">config.json completo (raw)</div>
      <textarea class="fi" id="c-raw" rows="10" style="font-family:monospace;font-size:12px;"></textarea>
    </div>
  </div>
</div>

</main>
</div>

<!-- MODAL ADD CLIENT -->
<div class="overlay" id="modal-add" onclick="closeModal(event,'modal-add')">
  <div class="modal">
    <div class="mttl">Añadir cliente <span class="mclose" onclick="closeM('modal-add')">×</span></div>
    <div class="fg"><label class="fl">Nombre del hotel</label>
      <input class="fi" id="ac-name" placeholder="Hotel Ejemplo Barcelona"></div>
    <div class="fg"><label class="fl">Ciudad</label>
      <input class="fi" id="ac-city" placeholder="Barcelona"></div>
    <div class="fg"><label class="fl">Email del director</label>
      <input class="fi" id="ac-email" type="email" placeholder="director@hotel.com"></div>
    <div class="fg"><label class="fl">Plan</label>
      <select class="fi" id="ac-plan">
        <option value="basic">Basic · 79€/mes</option>
        <option value="pro" selected>Pro · 149€/mes</option>
        <option value="premium">Premium · 299€/mes</option>
      </select></div>
    <button class="btn bp" style="width:100%;justify-content:center;" onclick="addClient()">
      Añadir cliente</button>
  </div>
</div>

<!-- MODAL REPORT VIEWER -->
<div class="overlay" id="modal-report" onclick="closeModal(event,'modal-report')">
  <div class="modal" style="max-width:800px;width:96%;">
    <div class="mttl" id="modal-report-title">Informe
      <span class="mclose" onclick="closeM('modal-report')">×</span></div>
    <div id="modal-report-body"></div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const API = '';
let _stats={}, _clients=[], _reports=[], _alerts=[], _cfg={};

async function api(path, method='GET', body=null){
  const o={method,headers:{'Content-Type':'application/json'}};
  if(body) o.body=JSON.stringify(body);
  const r=await fetch(API+path,o);
  return r.json();
}

function toast(msg,type=''){
  const t=document.getElementById('toast');
  t.textContent=msg; t.className='toast '+(type==='ok'?'ok':type==='err'?'err':'');
  t.style.display='block'; setTimeout(()=>t.style.display='none',3500);
}

function nav(page){
  document.querySelectorAll('[id^="pg-"]').forEach(p=>p.style.display='none');
  document.querySelectorAll('.ni').forEach(n=>n.classList.remove('on'));
  document.getElementById('pg-'+page).style.display='block';
  document.getElementById('nav-'+page).classList.add('on');
  if(page==='clients') renderClients();
  if(page==='reports') renderReports();
  if(page==='alerts')  renderAlerts();
  if(page==='config')  renderConfig();
  if(page==='run') toggleDemoWarning();
}

async function loadAll(){
  const [stats,clients,reports,alerts] = await Promise.all([
    api('/api/stats'), api('/api/clients'), api('/api/reports'), api('/api/alerts')
  ]);
  _stats=stats; _clients=clients; _reports=reports; _alerts=alerts;
  renderDash(); renderClients(); renderReports(); renderAlerts();
  document.getElementById('last-refresh').textContent=
    'Actualizado '+new Date().toLocaleTimeString('es-ES');
  document.getElementById('dash-ts').textContent=
    new Date().toLocaleDateString('es-ES',{weekday:'long',day:'numeric',month:'long'});

  // badge alertas hoy
  const today=new Date().toISOString().slice(0,10);
  const todayAlerts=alerts.filter(a=>a.created_at&&a.created_at.startsWith(today));
  const ab=document.getElementById('ab');
  if(todayAlerts.length){ab.textContent=todayAlerts.length;ab.style.display='inline';}
  else ab.style.display='none';
}

// ── DASHBOARD ──
function renderDash(){
  const s=_stats;
  document.getElementById('mrow').innerHTML=`
    <div class="mc hi"><div class="ml">Clientes activos</div>
      <div class="mv">${s.active_clients||0}</div>
      <div class="ms">de ${s.total_clients||0} registrados</div></div>
    <div class="mc"><div class="ml">Informes hoy</div>
      <div class="mv">${s.reports_today||0}</div>
      <div class="ms">${s.total_reports||0} total</div></div>
    <div class="mc"><div class="ml">Alertas hoy</div>
      <div class="mv">${s.alerts_today||0}</div>
      <div class="ms">${s.total_alerts||0} total</div></div>
    <div class="mc"><div class="ml">Planes</div>
      <div style="font-size:12px;margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;">
        <span class="bbasic">Basic ${s.plans?.basic||0}</span>
        <span class="bpro">Pro ${s.plans?.pro||0}</span>
        <span class="bprem">Prem ${s.plans?.premium||0}</span>
      </div></div>`;

  // últimos 5 informes
  document.getElementById('dash-rep').innerHTML=
    (_reports.slice(0,5).map(r=>`
      <tr style="cursor:pointer" onclick="viewReport(${r.id},'${r.subject||''}')">
        <td><strong>${r.subject||'—'}</strong><br>
          <span style="font-size:11px;color:var(--tx3)">${r.date||'—'}</span></td>
        <td><span class="b${r.status||'done'}">${r.status||'—'}</span></td>
      </tr>`).join('')) || '<tr><td colspan="2" style="color:var(--tx3);padding:12px">Sin informes</td></tr>';

  // últimas 5 alertas
  const dotColors={high:'var(--r)',medium:'var(--a)',low:'var(--g)'};
  document.getElementById('dash-alrt').innerHTML=
    (_alerts.slice(0,5).map(a=>`
      <div class="logitem">
        <div class="logdot" style="background:${dotColors[a.priority]||'var(--tx3)'}"></div>
        <div>
          <div class="logtxt">${a.title||a.trigger_type}</div>
          <div class="logdate">${(a.created_at||'').slice(0,16).replace('T',' ')} · ${a.hotel_name||''}</div>
        </div>
      </div>`).join('')) ||
    '<div style="color:var(--tx3);font-size:13px;padding:8px 0">Sin alertas registradas</div>';
}

// ── CLIENTS ──
function renderClients(){
  const planBadge=p=>p==='premium'?`<span class="bprem">Premium</span>`:
    p==='pro'?`<span class="bpro">Pro</span>`:`<span class="bbasic">Basic</span>`;
  document.getElementById('clients-body').innerHTML=
    _clients.map(c=>`
      <tr>
        <td><strong>${c.name}</strong></td>
        <td>${c.city||'—'}</td>
        <td style="font-size:12px;color:var(--tx2)">${c.email}</td>
        <td>${planBadge(c.plan)}</td>
        <td><span class="${c.active?'bon':'boff'}">${c.active?'Activo':'Pausado'}</span></td>
        <td style="font-size:12px;color:var(--tx3)">${(c.created_at||'').slice(0,10)}</td>
        <td>
          <button class="btn bs" style="font-size:11px;padding:4px 10px"
            onclick="quickRun('${c.name}','${c.city||''}',${c.id})">▷ Analizar</button>
          <select style="font-size:11px;padding:4px 6px;border:1px solid var(--b);
                         border-radius:6px;background:var(--s);cursor:pointer;margin-left:4px;"
            onchange="changePlan(${c.id},this.value)">
            <option ${c.plan==='basic'?'selected':''} value="basic">Basic</option>
            <option ${c.plan==='pro'?'selected':''} value="pro">Pro</option>
            <option ${c.plan==='premium'?'selected':''} value="premium">Premium</option>
          </select>
        </td>
      </tr>`).join('') ||
    '<tr><td colspan="7" style="padding:20px;color:var(--tx3);text-align:center">Sin clientes. Añade el primero.</td></tr>';
}

// ── REPORTS ──
function renderReports(){
  const clientName=id=>{const c=_clients.find(x=>x.id===id);return c?c.name:'-';};
  document.getElementById('reports-body').innerHTML=
    _reports.map(r=>`
      <tr>
        <td><strong>${clientName(r.hotel_id)}</strong></td>
        <td>${r.date||'—'}</td>
        <td><span class="b${r.status||'done'}">${r.status||'—'}</span></td>
        <td style="font-size:12px;color:var(--tx2);max-width:280px;
                   white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
          ${r.subject||'—'}</td>
        <td><button class="btn bs" style="font-size:11px;padding:4px 10px"
          onclick="viewReport(${r.id},'${(r.subject||'').replace(/'/g,"\\'")}')">Ver email</button></td>
      </tr>`).join('') ||
    '<tr><td colspan="5" style="padding:20px;color:var(--tx3);text-align:center">Sin informes aún</td></tr>';
}

// ── ALERTS ──
function renderAlerts(){
  const dotColors={high:'var(--r)',medium:'var(--a)',low:'var(--g)'};
  const pLabels={high:'Urgente',medium:'Importante',low:'Info'};
  document.getElementById('alerts-body').innerHTML=
    _alerts.map(a=>`
      <div class="logitem">
        <div class="logdot" style="background:${dotColors[a.priority||'medium']||'var(--tx3)'}"></div>
        <div style="flex:1">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:3px;">
            <span class="b${a.priority||'med'}">${pLabels[a.priority]||a.priority}</span>
            <span style="font-size:13px;font-weight:500">${a.title||a.trigger_type}</span>
          </div>
          <div style="font-size:12px;color:var(--tx2)">${a.hotel_name||''} · ${a.trigger_type||''}</div>
          ${a.recommendation?`<div style="font-size:12px;color:var(--g);margin-top:3px">→ ${a.recommendation}</div>`:''}
        </div>
        <div style="font-size:11px;color:var(--tx3);white-space:nowrap">
          ${(a.created_at||'').slice(0,16).replace('T',' ')}</div>
      </div>`).join('') ||
    '<div style="color:var(--tx3);font-size:13px;padding:8px 0">Sin alertas registradas</div>';
}

// ── CONFIG ──
async function renderConfig(){
  const r=await fetch('/api/preview/config.json').catch(()=>null);
  let cfg={};
  try{const raw=await fetch('/api/stats');cfg=await raw.json();} catch(e){}

  try{
    const rr=await fetch('/'+CONFIG_FILE).catch(()=>null);
    if(rr&&rr.ok) cfg=await rr.json();
  }catch(e){}

  // Leer config.json directamente via endpoint dedicado
  try{
    const cr=await api('/api/config');
    if(cr&&!cr.error) cfg=cr;
  }catch(e){}

  document.getElementById('c-name').value=cfg.name||'';
  document.getElementById('c-city').value=cfg.city||'';
  document.getElementById('c-apikey').value=cfg.anthropic_api_key||'';
  document.getElementById('c-smtp').value=cfg.smtp_email||'';
  document.getElementById('c-smtppass').value=cfg.smtp_password||'';
  document.getElementById('c-recipient').value=cfg.report_recipient||'';
  document.getElementById('c-raw').value=JSON.stringify(cfg,null,2);
  _cfg=cfg;
}

async function saveConfig(){
  let cfg;
  try{cfg=JSON.parse(document.getElementById('c-raw').value);}
  catch(e){toast('JSON inválido','err');return;}
  cfg.name=document.getElementById('c-name').value||cfg.name;
  cfg.city=document.getElementById('c-city').value||cfg.city;
  cfg.anthropic_api_key=document.getElementById('c-apikey').value||cfg.anthropic_api_key;
  cfg.smtp_email=document.getElementById('c-smtp').value||cfg.smtp_email;
  cfg.smtp_password=document.getElementById('c-smtppass').value||cfg.smtp_password;
  cfg.report_recipient=document.getElementById('c-recipient').value||cfg.report_recipient;
  const r=await api('/api/save-config','POST',cfg);
  toast(r.ok?'Configuración guardada':'Error guardando',r.ok?'ok':'err');
}

// ── ACTIONS ──
async function quickRun(name,city,id){
  const r=await api('/api/run-analysis','POST',{hotel_name:name,city,hotel_id:id});
  toast(r.ok?`Análisis iniciado para ${name} (~90s)`:(r.error||'Error'),r.ok?'ok':'err');
  nav('run');
  document.getElementById('run-hotel').value=name;
  document.getElementById('run-city').value=city;
}

function showPreviewAndDone(btn,btxt,status,jobId){
  btn.disabled=false; btxt.textContent='▷ Generar informe';
  status.style.display='none';
  status.style.background=''; status.style.color='';
  toast('¡Análisis completado!','ok');
  const src=jobId ? ('/api/preview/job/'+encodeURIComponent(jobId)+'?t='+Date.now()) : ('/api/preview/report_preview.html?t='+Date.now());
  document.getElementById('preview-area').innerHTML=
    '<div class="iframe-wrap"><iframe src="'+src+'" height="500" onload="this.style.height=(this.contentWindow.document.body.scrollHeight+20)+\'px\'"></iframe></div>';
  loadAll();
}

// Mensajes por fase (progreso real)
const STAGE_MESSAGES={
  created:'Preparando...',
  starting:'Iniciando análisis...',
  discovery:'Identificando hotel...',
  compset:'Detectando comp set...',
  parallel:'Revisando precios y disponibilidad...',
  pricing:'Revisando precios y disponibilidad...',
  demand:'Analizando demanda...',
  reputation:'Analizando reputación...',
  distribution:'Revisando distribución y paridad...',
  consolidate:'Calculando estrategia, alertas y oportunidades...',
  report:'Generando informe final...',
  rendering:'Generando vista previa del informe...',
  persisting:'Guardando informe...',
  notifying:'Enviando email...',
  done:'Completado.',
  error:'Error.'
};

function toggleDemoWarning(){
  const w=document.getElementById('run-demo-warning');
  const c=document.getElementById('run-fast-demo');
  w.style.display=c&&c.checked?'block':'none';
}

function renderProgressSteps(steps){
  const el=document.getElementById('run-progress-steps');
  if(!el) return;
  if(!steps||!steps.length){ el.style.display='none'; return; }
  el.style.display='block';
  const statusIcon=s=>{
    if(s==='done') return '<span style="color:var(--g)">✓</span>';
    if(s==='active') return '<span class="spin" style="display:inline-block;width:10px;height:10px;border:2px solid var(--bl);border-top-color:transparent;border-radius:50%;"></span>';
    if(s==='warning') return '<span style="color:var(--a)">⚠</span>';
    if(s==='error') return '<span style="color:var(--r)">✗</span>';
    return '<span style="color:var(--tx3)">○</span>';
  };
  el.innerHTML='<div style="font-weight:600;margin-bottom:8px;color:var(--tx2)">Progreso del análisis</div>'+
    steps.map(s=>'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;font-size:12px;">'+
      '<span style="width:18px;text-align:center">'+statusIcon(s.status)+'</span>'+
      '<span style="'+(s.status==='active'?'font-weight:600;color:var(--bl)':'color:var(--tx)')+'">'+s.label+'</span>'+
      '</div>').join('');
}

function renderEvidence(ev){
  const el=document.getElementById('run-evidence');
  if(!el) return;
  if(!ev){ el.style.display='none'; return; }
  el.style.display='block';
  const row=(label,val)=>'<tr><td style="color:var(--tx2);width:140px">'+label+'</td><td>'+val+'</td></tr>';
  el.innerHTML='<div class="card" style="margin-top:0"><div class="ct">Qué ha encontrado RevMax</div>'+
    '<table class="tbl" style="font-size:12px"><tbody>'+
    row('Hotel', ev.hotel_detected||'No encontrado')+
    row('Ciudad', ev.city||'No encontrado')+
    row('Precio propio', ev.own_price||'No encontrado')+
    row('Media compset', ev.compset_avg||'No encontrado')+
    row('Posición precio', ev.price_position||'No encontrado')+
    row('GRI / Reputación', ev.gri||'No encontrado')+
    row('Visibilidad', ev.visibility||'No encontrado')+
    row('Paridad', ev.parity_status||'No encontrado')+
    row('Demand score', ev.demand_score||'No encontrado')+
    row('Top 3 competidores', (ev.top_3_competitors||[]).join(', ')||'No encontrados')+
    row('Análisis', ev.is_degraded?'Degradado (algunos datos por fallback)':'Completo')+
    '</tbody></table></div>';
}

function renderQuality(q){
  const el=document.getElementById('run-quality');
  if(!el) return;
  if(!q){ el.style.display='none'; return; }
  el.style.display='block';
  const labelClass=q.label==='excellent'?'bdone':q.label==='good'?'bdone':q.label==='degraded'?'bmed':'bhigh';
  el.innerHTML='<div class="card" style="margin-top:0"><div class="ct">Salud del análisis</div>'+
    '<p style="margin:0 0 8px 0"><span class="'+labelClass+'">'+q.label.toUpperCase()+'</span> '+
    'Score: '+q.score+' · Agentes OK: '+q.agents_ok+'/'+q.agents_total+
    (q.fallback_count>0 ? ' · Fallbacks: '+q.fallback_count : '')+'</p>'+
    '<p style="margin:0;font-size:12px;color:var(--tx2)">'+q.summary+'</p></div>';
}

async function runAnalysis(){
  const hotel=document.getElementById('run-hotel').value.trim();
  const city=document.getElementById('run-city').value.trim();
  const mode=document.getElementById('run-mode').value;
  const fastDemo=document.getElementById('run-fast-demo').checked;
  if(!hotel){toast('Escribe el nombre del hotel','err');return;}

  const btn=document.getElementById('run-btn');
  const btxt=document.getElementById('run-btn-txt');
  btn.disabled=true;
  btxt.innerHTML='<span class="spin"></span> Analizando...';

  const status=document.getElementById('run-status');
  status.style.display='block';
  status.style.background='var(--blb);color:var(--bl);';
  status.textContent=fastDemo ? 'Demo rápido: preparando...' : 'Iniciando análisis...';

  const r=await api('/api/run-analysis','POST',{
    hotel_name:hotel, city, hotel_id:1,
    send_email: mode==='send',
    fast_demo: fastDemo
  });

  if(!r.ok){
    toast(r.error||'Error','err');
    btn.disabled=false; btxt.textContent='▷ Generar informe';
    status.style.display='none'; return;
  }

  const jobId=r.job_id||null;
  toast(fastDemo ? 'Demo iniciado (~20 s)' : 'Análisis iniciado (1–2 min)','ok');
  document.getElementById('run-evidence').style.display='none';
  document.getElementById('run-quality').style.display='none';

  let polls=0;
  const poll=setInterval(async()=>{
    polls++;
    if(polls>90){
      clearInterval(poll);
      btn.disabled=false; btxt.textContent='▷ Generar informe';
      status.textContent='Tardó más de lo esperado. Revisa data/admin_errors.log';
      status.style.background='var(--blb);color:var(--bl);';
      document.getElementById('run-progress-steps').style.display='none';
      loadAll();
      return;
    }
    if(jobId){
      const jR=await fetch('/api/job-status/'+jobId).catch(()=>null);
      if(jR&&jR.ok){
        const job=await jR.json();
        if(job.progress_steps&&job.progress_steps.length) renderProgressSteps(job.progress_steps);
        if(job.stage) status.textContent=(STAGE_MESSAGES[job.stage]||job.stage)+(job.progress_pct!=null?' · '+job.progress_pct+'%':'');
        if(job.status==='completed'){
          clearInterval(poll);
          if(job.evidence_found) renderEvidence(job.evidence_found);
          if(job.analysis_quality) renderQuality(job.analysis_quality);
          showPreviewAndDone(btn,btxt,status,jobId);
          return;
        }
        if(job.status==='failed'){
          clearInterval(poll);
          btn.disabled=false; btxt.textContent='▷ Generar informe';
          document.getElementById('run-progress-steps').style.display='none';
          status.style.display='block';
          status.style.background='#3d2020'; status.style.color='#f0a0a0';
          status.style.whiteSpace='pre-wrap'; status.style.textAlign='left';
          status.style.padding='12px'; status.style.maxHeight='220px'; status.style.overflowY='auto';
          status.textContent='Error: '+(job.error_message||'Unknown');
          toast('Análisis falló','err');
          return;
        }
        if(job.status==='stalled'){
          clearInterval(poll);
          btn.disabled=false; btxt.textContent='▷ Generar informe';
          document.getElementById('run-progress-steps').style.display='none';
          status.style.display='block';
          status.style.background='#3d2020'; status.style.color='#f0a0a0';
          status.style.whiteSpace='pre-wrap'; status.style.textAlign='left';
          status.style.padding='12px'; status.style.maxHeight='220px'; status.style.overflowY='auto';
          status.textContent='Job colgado: '+(job.error_message||'Sin actualización en el tiempo límite.');
          toast('Análisis colgado','err');
          return;
        }
        if(job.status==='cancelled'){
          clearInterval(poll);
          btn.disabled=false; btxt.textContent='▷ Generar informe';
          document.getElementById('run-progress-steps').style.display='none';
          status.style.display='block';
          status.style.background='var(--s2)'; status.style.color='var(--tx2)';
          status.textContent='Análisis cancelado.';
          toast('Análisis cancelado','err');
          return;
        }
        return;
      }
    }
    const stR=await fetch('/api/analysis-status').catch(()=>null);
    if(!stR||!stR.ok) return;
    const st=await stR.json();
    if(st.status==='success'){
      clearInterval(poll);
      showPreviewAndDone(btn,btxt,status,null);
      return;
    }
    if(st.status==='error'){
      clearInterval(poll);
      btn.disabled=false; btxt.textContent='▷ Generar informe';
      status.style.display='block';
      status.style.background='#3d2020'; status.style.color='#f0a0a0';
      status.style.whiteSpace='pre-wrap'; status.style.textAlign='left';
      status.style.padding='12px'; status.style.maxHeight='220px'; status.style.overflowY='auto';
      status.textContent='Error: '+(st.error||'Unknown')+(st.source?'\n\nOrigen: '+st.source:'')+(st.exc_type?'\nTipo: '+st.exc_type:'');
      toast('Análisis falló','err');
    }
  },2000);
}

async function viewReport(id,subject){
  document.getElementById('modal-report-title').innerHTML=
    `${subject||'Informe'} <span class="mclose" onclick="closeM('modal-report')">×</span>`;
  document.getElementById('modal-report-body').innerHTML=
    `<div class="iframe-wrap"><iframe src="/api/report-html/${id}"
       height="600" onload="this.style.height=(this.contentWindow.document.body.scrollHeight+20)+'px'">
     </iframe></div>`;
  document.getElementById('modal-report').classList.add('open');
}

async function changePlan(id,plan){
  await api('/api/update-plan','POST',{hotel_id:id,plan});
  toast(`Plan actualizado a ${plan}`,'ok');
  await loadAll();
}

function openAddClient(){document.getElementById('modal-add').classList.add('open');}
function closeM(id){document.getElementById(id).classList.remove('open');}
function closeModal(e,id){if(e.target.id===id)closeM(id);}

async function addClient(){
  const r=await api('/api/add-client','POST',{
    name:document.getElementById('ac-name').value,
    city:document.getElementById('ac-city').value,
    email:document.getElementById('ac-email').value,
    plan:document.getElementById('ac-plan').value,
  });
  toast(r.message||r.error, r.ok?'ok':'err');
  closeM('modal-add');
  await loadAll();
}

// ── INIT ──
window.onload=()=>{loadAll();setInterval(loadAll,60000);};
</script>
</body></html>"""


@app.get("/", response_class=HTMLResponse)
def serve_admin():
    return HTML


@app.get("/api/config")
def api_get_config():
    return load_config()


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
