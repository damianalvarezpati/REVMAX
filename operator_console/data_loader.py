"""
RevMax — Operator Console — Data Loader
========================================
Carga de datos, ejecución de análisis y QA.
No modifica job engine ni engines; solo orquesta y lee.
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional

# Asegurar import desde raíz del proyecto
_CONSOLE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_CONSOLE_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def load_config() -> dict:
    path = os.path.join(_PROJECT_ROOT, "config.json")
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_api_key() -> str:
    cfg = load_config()
    key = cfg.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
    return key.strip()


def run_analysis(
    hotel_name: str,
    city: str = "",
    fast_demo: bool = True,
) -> Dict[str, Any]:
    """
    Ejecuta un análisis (fast_demo o full) y devuelve full_analysis.
    Bloqueante: usa asyncio.run() para el pipeline async.
    """
    api_key = get_api_key()
    if not api_key:
        return {"error": "Falta ANTHROPIC_API_KEY en config.json o entorno."}

    async def _run():
        if fast_demo:
            from orchestrator import run_fast_demo
            return await run_fast_demo(
                hotel_name=hotel_name,
                city_hint=city,
                api_key=api_key,
                progress_callback=lambda s, p: None,
            )
        from orchestrator import run_full_analysis
        return await run_full_analysis(
            hotel_name=hotel_name,
            city_hint=city,
            api_key=api_key,
            progress_callback=lambda s, p: None,
        )

    try:
        return asyncio.run(_run())
    except Exception as e:
        return {"error": str(e)}


def build_qa_case_from_analysis(full_analysis: dict) -> Optional[str]:
    """
    Construye y guarda un caso QA desde full_analysis.
    Devuelve la ruta del archivo guardado o None si falla.
    """
    if full_analysis.get("error"):
        return None
    try:
        from qa_runner import run_qa_from_full_analysis
        case = run_qa_from_full_analysis(full_analysis, base_dir=_PROJECT_ROOT)
        return case.get("_saved_path")
    except Exception:
        return None


def get_report_display(full_analysis: dict) -> Dict[str, Any]:
    """Extrae datos para el panel Informe: resumen, estrategia, riesgos, acciones, oportunidades, escenario, cambios."""
    if not full_analysis or full_analysis.get("error"):
        return {}
    briefing = full_analysis.get("briefing") or {}
    report = full_analysis.get("report") or {}

    seed = briefing.get("executive_summary_seed") or []
    executive_summary = "\n".join(seed) if seed else (report.get("report_text") or "")[:500]

    strategy = briefing.get("strategy_label") or "—"
    strategy_rationale = briefing.get("strategy_rationale") or ""

    top_risks = briefing.get("executive_top_risks") or []
    risks_text = []
    for r in top_risks[:5]:
        if isinstance(r, dict):
            risks_text.append(f"• [{r.get('severity', '?')}] {r.get('type', '?')}: {(r.get('message') or '')[:120]}")
        else:
            risks_text.append(str(r))

    actions = report.get("priority_actions") or briefing.get("executive_top_actions") or []
    actions_text = []
    for a in actions[:5]:
        if isinstance(a, dict):
            actions_text.append(f"• {a.get('action', a.get('title', '?'))} — {a.get('reason', '')[:80]}")
        else:
            actions_text.append(str(a))

    opportunities = briefing.get("executive_top_opportunities") or briefing.get("opportunities") or []
    opps_text = []
    for o in opportunities[:5]:
        if isinstance(o, dict):
            opps_text.append(f"• {o.get('title', o.get('type', '?'))}: {(o.get('summary') or '')[:80]}")
        else:
            opps_text.append(str(o))

    scenario = briefing.get("recommended_scenario") or report.get("recommended_scenario") or "—"
    scenario_summary = briefing.get("scenario_summary") or ""

    change_summary = briefing.get("change_summary") or "—"
    change_severity = briefing.get("change_severity") or "—"
    change_highlights = briefing.get("change_highlights") or []

    return {
        "executive_summary": executive_summary,
        "strategy": strategy,
        "strategy_rationale": strategy_rationale,
        "top_risks": risks_text,
        "recommended_actions": actions_text,
        "top_opportunities": opps_text,
        "scenario_recommendation": scenario,
        "scenario_summary": scenario_summary,
        "change_summary": change_summary,
        "change_severity": change_severity,
        "change_highlights": change_highlights,
        "report_text": report.get("report_text", ""),
        "overall_status": report.get("overall_status") or briefing.get("derived_overall_status") or "—",
    }


def get_reasoning_display(full_analysis: dict) -> Dict[str, Any]:
    """Extrae datos para el panel Razonamiento: observed facts, interpreted signals, value, scenario, change."""
    if not full_analysis or full_analysis.get("error"):
        return {}
    briefing = full_analysis.get("briefing") or {}

    try:
        from qa_case_builder import build_validation_case_from_briefing
        hotel = full_analysis.get("hotel_name", "?")
        case = build_validation_case_from_briefing(briefing, hotel)
        observed = case.get("observed_facts") or {}
        interpreted = case.get("interpreted_signals") or {}
    except Exception:
        observed = {}
        interpreted = {}

    top_priority = briefing.get("top_priority_item")
    value_opps = briefing.get("value_opportunities") or []
    value_acts = briefing.get("value_actions") or []
    value_summary = briefing.get("value_summary") or "—"

    scenario_assessment = briefing.get("scenario_assessment") or []
    scenario_list = []
    for a in scenario_assessment:
        if isinstance(a, dict):
            scenario_list.append({
                "scenario": a.get("scenario", "?"),
                "support": a.get("support_score"),
                "risk": a.get("risk_score"),
                "net": a.get("net_score"),
            })

    change_summary = briefing.get("change_summary") or "—"
    change_severity = briefing.get("change_severity") or "—"
    change_highlights = briefing.get("change_highlights") or []

    return {
        "observed_facts": observed,
        "interpreted_signals": interpreted,
        "value_summary": value_summary,
        "top_priority_item": top_priority,
        "value_opportunities": value_opps[:5],
        "value_actions": value_acts[:5],
        "scenario_analysis": scenario_list,
        "change_summary": change_summary,
        "change_severity": change_severity,
        "change_highlights": change_highlights,
    }


def load_qa_cases(limit: int = 100) -> List[dict]:
    """Carga casos desde data/qa_runs/."""
    try:
        from qa_registry import load_validation_cases
        return load_validation_cases(base_dir=_PROJECT_ROOT, limit=limit)
    except Exception:
        return []


def get_qa_decision_summary() -> Dict[str, Any]:
    """Resumen para diagnóstico del modelo."""
    try:
        from qa_registry import load_validation_cases, build_qa_decision_summary
        cases = load_validation_cases(base_dir=_PROJECT_ROOT, limit=200)
        return build_qa_decision_summary(cases)
    except Exception:
        return {}


def apply_validation(
    case_path: str,
    score: Optional[int] = None,
    feedback: Optional[str] = None,
    verdict: Optional[str] = None,
    adjustment_decision: Optional[str] = None,
) -> dict:
    """Aplica revisión humana al caso en case_path."""
    try:
        from pathlib import Path

        from qa_registry import apply_human_review

        out = apply_human_review(
            case_path,
            score=score,
            feedback=feedback,
            verdict=verdict,
            adjustment_decision=adjustment_decision,
        )
        try:
            from dojo_validation_debt import mark_validation_tasks_done_for_case_path

            base = Path(__file__).resolve().parent.parent
            mark_validation_tasks_done_for_case_path(base, case_path)
        except Exception:
            pass
        return out
    except Exception as e:
        return {"error": str(e)}


def load_case_by_path(path: str) -> Optional[dict]:
    """Carga un caso desde su ruta."""
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
