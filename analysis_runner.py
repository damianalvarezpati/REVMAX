"""
RevMax — Orquestación de la ejecución de un análisis por job.
Separa: ejecutar pipeline, renderizar artefactos, persistir en DB, notificar (email), marcar fallo.
Heartbeat actualiza updated_at durante la ejecución; se cancela al terminar o al timeout.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import job_state
from error_utils import get_error_source
from report_artifacts import write_preview, write_result_report

PIPELINE_TIMEOUT_SECONDS = 600
HEARTBEAT_INTERVAL_SECONDS = 20


def _jobs_dir(base_dir: str) -> str:
    return os.path.join(base_dir, "data", "jobs")


def _job_meta_path(base_dir: str, job_id: str) -> str:
    return os.path.join(_jobs_dir(base_dir), f"{job_id}_meta.json")


def _job_progress_path(base_dir: str, job_id: str) -> str:
    return os.path.join(_jobs_dir(base_dir), f"{job_id}_progress.json")


def write_job_progress(base_dir: str, job_id: str, steps: List[Dict[str, Any]]) -> None:
    """Escribe pasos de progreso para la UI (sin tocar job_state)."""
    path = _job_progress_path(base_dir, job_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"steps": steps, "updated_at": datetime.utcnow().isoformat() + "Z"}, f, ensure_ascii=False)
    except Exception:
        pass


def write_job_meta(
    base_dir: str,
    job_id: str,
    analysis_timing: Dict[str, float],
    analysis_quality: Dict[str, Any],
    evidence_found: Dict[str, Any],
    progress_steps: Optional[List[Dict[str, Any]]] = None,
    result_summary: Optional[Dict[str, Any]] = None,
) -> None:
    """Escribe meta del análisis al completar (timing, calidad, evidencias, pasos, resumen decisión)."""
    path = _job_meta_path(base_dir, job_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        data = {
            "analysis_timing": analysis_timing,
            "analysis_quality": analysis_quality,
            "evidence_found": evidence_found,
            "progress_steps": progress_steps or [],
            "result_summary": result_summary or {},
            "completed_at": datetime.utcnow().isoformat() + "Z",
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def read_job_meta(base_dir: str, job_id: str) -> Optional[Dict[str, Any]]:
    """Lee meta del análisis si existe."""
    path = _job_meta_path(base_dir, job_id)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def read_job_progress(base_dir: str, job_id: str) -> Optional[List[Dict[str, Any]]]:
    """Lee pasos de progreso si existen."""
    path = _job_progress_path(base_dir, job_id)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return data.get("steps")
    except Exception:
        return None


# Misma definición de pasos que orchestrator.PROGRESS_STEP_LABELS para fallback en api_job_status
_FALLBACK_STEP_LABELS = [
    (1, "discovery", "Identificando hotel"),
    (2, "compset", "Detectando comp set"),
    (3, "pricing", "Revisando precios y disponibilidad"),
    (4, "demand", "Analizando demanda"),
    (5, "reputation", "Analizando reputación"),
    (6, "distribution", "Revisando distribución y paridad"),
    (7, "consolidate", "Calculando estrategia, alertas y oportunidades"),
    (8, "consolidate", "Priorizando acciones y escenarios"),
    (9, "report", "Generando informe final"),
]
_STAGE_ORDER = {"starting": 0, "discovery": 1, "compset": 2, "parallel": 3, "pricing": 3, "demand": 3, "reputation": 3, "distribution": 3, "consolidate": 4, "report": 5, "rendering": 6, "persisting": 7, "notifying": 8, "done": 9, "error": -1, "created": -1}


def build_fallback_progress_steps(stage: str, status: str, progress_pct: int = 0) -> List[Dict[str, Any]]:
    """Construye 9 pasos cuando no hay progress escrito; usado por api_job_status."""
    order = _STAGE_ORDER.get(stage, -1)
    steps = []
    for step_id, stage_key, label in _FALLBACK_STEP_LABELS:
        step_order = _STAGE_ORDER.get(stage_key, -1)
        s = {"id": step_id, "label": label, "status": "pending"}
        if stage_key == stage or (stage in ("starting", "created") and step_id == 1):
            s["status"] = "error" if status == "failed" else "active"
        elif step_order >= 0 and order >= 0 and step_order < order:
            s["status"] = "done"
        steps.append(s)
    return steps


async def _heartbeat_loop(base_dir: str, job_id: str) -> None:
    """
    Loop que actualiza updated_at del job cada HEARTBEAT_INTERVAL_SECONDS.
    Se cancela desde fuera (CancelledError); no debe quedar corriendo al terminar el job.
    """
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
        job_state.touch_job(base_dir, job_id)


def _make_progress_callback(base_dir: str, job_id: str) -> Callable[..., None]:
    """Callback que actualiza job_state y opcionalmente escribe progress_steps en _progress.json."""

    def cb(stage: str, progress_pct: int, steps: Optional[List[Dict[str, Any]]] = None) -> None:
        job_state.update_job(base_dir, job_id, stage=stage, progress_pct=progress_pct)
        if steps is not None:
            write_job_progress(base_dir, job_id, steps)

    return cb


async def run_pipeline(
    hotel_name: str,
    city: str,
    api_key: str,
    fast_demo: bool,
    progress_callback: Callable[..., None],
) -> dict:
    """
    Ejecuta el pipeline de análisis (completo o demo).
    Devuelve el resultado full_analysis con report.
    """
    if fast_demo:
        from orchestrator import run_fast_demo
        return await run_fast_demo(
            hotel_name=hotel_name,
            city_hint=city,
            api_key=api_key,
            progress_callback=progress_callback,
        )
    from orchestrator import run_full_analysis
    return await run_full_analysis(
        hotel_name=hotel_name,
        city_hint=city,
        api_key=api_key,
        progress_callback=progress_callback,
    )


def _error_html(hotel_name: str, error_message: str) -> str:
    """HTML mínimo para mostrar en el iframe cuando falla generación o no hay informe."""
    from html import escape
    msg = escape(str(error_message))
    name = escape(str(hotel_name or "Hotel"))
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>RevMax — Error</title></head>
<body style="margin:0;padding:24px;background:#F0EDE6;font-family:-apple-system,sans-serif;">
<div style="max-width:560px;margin:20px auto;background:#FAECE7;border:1px solid #D85A30;border-radius:12px;padding:24px;">
  <div style="font-size:14px;font-weight:700;color:#712B13;margin-bottom:8px;">No se pudo generar el informe</div>
  <div style="font-size:13px;color:#2C2C2A;">{name}</div>
  <pre style="margin:12px 0 0;padding:12px;background:#fff;border-radius:6px;font-size:12px;overflow:auto;white-space:pre-wrap;">{msg}</pre>
</div>
</body></html>"""


def _normalize_report_for_html(report: dict, hotel_name: str) -> dict:
    """Asegura que el report tenga todas las claves que build_email_html_v2 espera."""
    out = dict(report)
    out.setdefault("report_text", "")
    if not isinstance(out["report_text"], str):
        out["report_text"] = str(out["report_text"])
    out.setdefault("overall_status", "stable")
    out.setdefault("priority_actions", [])
    if not isinstance(out["priority_actions"], list):
        out["priority_actions"] = []
    out.setdefault("weekly_watchlist", "")
    out.setdefault("status_summary", "")
    out.setdefault("email_subject", f"RevMax · {hotel_name}")
    return out


def render_artifacts(
    base_dir: str,
    job_id: str,
    hotel_name: str,
    result: dict,
) -> Tuple[str, str, str]:
    """
    Genera HTML del informe, escribe preview por job y reporte en reports/.
    Devuelve (preview_path_rel, result_path_rel, html).
    """
    from mailer.report_mailer_v2 import build_email_html_v2
    report = result.get("report", {}) or {}
    if not report:
        report = {
            "report_text": "No hay informe disponible. Puede que el análisis no haya llegado a generar el reporte.",
            "overall_status": "stable",
            "priority_actions": [],
            "weekly_watchlist": "",
            "status_summary": "Sin datos.",
            "email_subject": f"RevMax · {hotel_name}",
        }
    report = _normalize_report_for_html(report, hotel_name)
    try:
        html = build_email_html_v2(result, report)
    except Exception as e:
        html = _error_html(hotel_name, f"Error al generar el HTML del informe: {e}")
    preview_rel = write_preview(base_dir, job_id, html)
    result_rel = write_result_report(base_dir, hotel_name, html)
    return preview_rel, result_rel, html


def persist_report_to_db(
    conn,
    hotel_id: int,
    report: dict,
    result_html_path: str,
) -> None:
    """
    Inserta el informe en la tabla reports.
    result_html_path: ruta relativa al proyecto (ej: data/reports/Hotel_20250314_1201.html).
    conn: conexión SQLite con row_factory (portal_db).
    """
    if conn is None:
        return
    try:
        conn.execute(
            "INSERT INTO reports (hotel_id, date, status, overall, subject, report_text, actions, html_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                hotel_id,
                datetime.now().strftime("%Y-%m-%d"),
                "done",
                report.get("overall_status"),
                report.get("email_subject"),
                report.get("report_text"),
                json.dumps(report.get("priority_actions", [])),
                result_html_path,
            ),
        )
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass


def try_send_report_email(
    cfg: dict,
    html: str,
    report: dict,
    hotel_name: str,
) -> Optional[str]:
    """
    Envía el email del informe si cfg lo permite.
    Devuelve None si se envió bien, o el mensaje de error si falló (sin lanzar).
    """
    smtp_email = cfg.get("smtp_email", "")
    smtp_password = cfg.get("smtp_password", "")
    recipient = cfg.get("report_recipient", smtp_email)
    if not smtp_email or not smtp_password or not recipient:
        return None
    try:
        from mailer.report_mailer_v2 import send_email as do_send_email
        do_send_email(
            html,
            report.get("email_subject", f"RevMax · {hotel_name}"),
            recipient,
            smtp_email,
            smtp_password,
        )
        return None
    except Exception as e:
        return str(e)


def mark_job_failed(
    base_dir: str,
    job_id: str,
    error_message: str,
) -> None:
    """Marca el job como failed y registra completed_at."""
    now_iso = datetime.utcnow().isoformat() + "Z"
    job_state.update_job(
        base_dir,
        job_id,
        status="failed",
        stage="error",
        error_message=error_message,
        completed_at=now_iso,
    )


def mark_job_cancelled(
    base_dir: str,
    job_id: str,
    message: str = "Cancelado por el usuario.",
) -> None:
    """Marca el job como cancelled (estado terminal) y registra completed_at."""
    now_iso = datetime.utcnow().isoformat() + "Z"
    job_state.update_job(
        base_dir,
        job_id,
        status="cancelled",
        stage="error",
        error_message=message,
        completed_at=now_iso,
    )


def _normalize_error_message(exc: Exception) -> str:
    """Mensaje de error legible para el usuario (créditos, auth, etc.)."""
    err_msg = str(exc)
    if "credit balance is too low" in err_msg.lower() or "credits" in err_msg.lower():
        return "Saldo de créditos insuficiente en Anthropic. Añade créditos en console.anthropic.com → Plans & Billing."
    if len(err_msg) > 300:
        return err_msg[:300] + "…"
    return err_msg


async def run_analysis_job(
    base_dir: str,
    job_id: str,
    hotel_name: str,
    city: str,
    api_key: str,
    hotel_id: int,
    cfg: dict,
    send_email: bool,
    fast_demo: bool,
    get_db_conn: Optional[Callable] = None,
    on_legacy_success: Optional[Callable[[], None]] = None,
    on_legacy_error: Optional[Callable[[str, str, str], None]] = None,
    pipeline_timeout_seconds: Optional[int] = None,
) -> None:
    """
    Ejecuta el análisis completo para un job: pipeline (con timeout), render, persist, notificar.
    Heartbeat actualiza updated_at cada HEARTBEAT_INTERVAL_SECONDS; se cancela al terminar o al timeout.
    Si el email falla tras éxito del análisis, el job queda completed con warning_message.
    """
    timeout = pipeline_timeout_seconds if pipeline_timeout_seconds is not None else PIPELINE_TIMEOUT_SECONDS
    now_iso = datetime.utcnow().isoformat() + "Z"
    job_state.update_job(
        base_dir,
        job_id,
        status="running",
        stage="starting",
        progress_pct=0,
        started_at=now_iso,
    )

    # Escribir pasos iniciales de inmediato para que la UI tenga siempre 9 pasos desde el primer poll
    try:
        from orchestrator import _build_progress_steps
        initial_steps = _build_progress_steps("starting", 5, [], False)
        write_job_progress(base_dir, job_id, initial_steps)
        print(f"[RevMax] job_id={job_id} initial progress_steps written: {len(initial_steps)} steps", flush=True)
    except Exception as e:
        print(f"[RevMax] job_id={job_id} failed to write initial steps: {e}", flush=True)

    progress_cb = _make_progress_callback(base_dir, job_id)
    heartbeat_task: Optional[asyncio.Task] = None

    try:
        heartbeat_task = asyncio.create_task(_heartbeat_loop(base_dir, job_id))
        try:
            result = await asyncio.wait_for(
                run_pipeline(
                    hotel_name=hotel_name,
                    city=city,
                    api_key=api_key,
                    fast_demo=fast_demo,
                    progress_callback=progress_cb,
                ),
                timeout=float(timeout),
            )
        except asyncio.TimeoutError:
            mark_job_failed(
                base_dir,
                job_id,
                f"Pipeline superó el tiempo límite ({timeout} s). Revisa datos o aumenta pipeline_timeout_seconds.",
            )
            if on_legacy_error:
                on_legacy_error(
                    f"Timeout {timeout}s",
                    "Orquestador (timeout)",
                    "TimeoutError",
                )
            return

        report = result.get("report", {})

        job_state.update_job(base_dir, job_id, status="rendering", stage="rendering", progress_pct=88)
        warning_message: Optional[str] = None
        try:
            preview_rel, result_rel, html = render_artifacts(base_dir, job_id, hotel_name, result)
        except Exception as e:
            err_msg = str(e)
            warning_message = err_msg
            html = _error_html(hotel_name, f"Error al renderizar el informe: {err_msg}")
            preview_rel = write_preview(base_dir, job_id, html)
            result_rel = write_result_report(base_dir, hotel_name, html)

        job_state.update_job(
            base_dir,
            job_id,
            status="persisting",
            stage="persisting",
            progress_pct=92,
            preview_html_path=preview_rel,
            result_html_path=result_rel,
        )

        conn = get_db_conn() if get_db_conn else None
        persist_report_to_db(conn, hotel_id, report, result_rel)

        if send_email and warning_message is None:
            job_state.update_job(base_dir, job_id, status="notifying", stage="notifying", progress_pct=95)
            warning_message = try_send_report_email(cfg, html, report, hotel_name)

        completed_at = datetime.utcnow().isoformat() + "Z"
        job_state.update_job(
            base_dir,
            job_id,
            status="completed",
            stage="done",
            progress_pct=100,
            completed_at=completed_at,
            warning_message=warning_message,
        )

        if not fast_demo and result.get("analysis_timing") is not None:
            briefing = result.get("briefing", {})
            report = result.get("report", {})
            conf = briefing.get("system_confidence")
            if conf is not None and isinstance(conf, (int, float)):
                confidence_pct = int(round(conf * 100))
            else:
                confidence_pct = 70
            consolidated = (briefing.get("consolidated_price_action") or report.get("overall_status") or "hold").lower()
            if consolidated not in ("raise", "hold", "lower", "promo"):
                consolidated = "hold"
            exec_summary = (
                (report.get("status_summary") or "")
                or (briefing.get("consolidation_rationale") or "")
                or (report.get("report_text") or "")[:300]
            )
            result_summary = {
                "consolidated_action": consolidated,
                "confidence_pct": confidence_pct,
                "executive_summary": exec_summary.strip() or "No summary available.",
                "analysis_date": result.get("analysis_date", datetime.now().strftime("%Y-%m-%d")),
            }
            write_job_meta(
                base_dir,
                job_id,
                result.get("analysis_timing", {}),
                result.get("analysis_quality", {}),
                result.get("evidence_found", {}),
                result.get("progress_steps"),
                result_summary=result_summary,
            )

        if on_legacy_success:
            on_legacy_success()

    except asyncio.CancelledError:
        mark_job_cancelled(base_dir, job_id)
        if on_legacy_error:
            on_legacy_error("Cancelado", "sistema", "CancelledError")
        raise
    except Exception as e:
        err_msg = _normalize_error_message(e)
        mark_job_failed(base_dir, job_id, err_msg)
        print(f"[RevMax] job_id={job_id} analysis failed: {err_msg}", flush=True)
        # Marcar el paso actual como error para que la UI muestre en qué paso falló
        try:
            job = job_state.get_job(base_dir, job_id)
            if job:
                stage = job.get("stage") or "starting"
                from orchestrator import _build_progress_steps
                steps = _build_progress_steps(stage, job.get("progress_pct") or 0, [], False)
                for s in steps:
                    if s.get("status") == "active":
                        s["status"] = "error"
                        break
                write_job_progress(base_dir, job_id, steps)
                print(f"[RevMax] job_id={job_id} progress_steps updated with error at stage={stage}", flush=True)
        except Exception:
            pass
        if on_legacy_error:
            on_legacy_error(err_msg, get_error_source(e), type(e).__name__)
        raise
    finally:
        if heartbeat_task is not None and not heartbeat_task.done():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
