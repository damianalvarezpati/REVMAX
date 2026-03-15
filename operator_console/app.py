"""
RevMax — Operator Console
==========================
Consola interna para operar RevMax y entrenar el modelo con casos reales.
Generar análisis, revisar decisiones, validar casos, puntuar razonamiento.
"""

import os
import sys

# Raíz del proyecto para imports de data_loader (orchestrator, qa_registry, etc.)
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_APP_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Para que Streamlit encuentre módulos en operator_console/
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

import streamlit as st
from data_loader import (
    run_analysis,
    build_qa_case_from_analysis,
    get_report_display,
    get_reasoning_display,
    load_qa_cases,
    get_qa_decision_summary,
    apply_validation,
    load_case_by_path,
)


def _run_analysis(hotel_name: str, city: str, fast_demo: bool) -> None:
    with st.spinner("Ejecutando análisis..."):
        result = run_analysis(hotel_name, city, fast_demo)
    if result.get("error"):
        st.error(result["error"])
        return
    st.session_state["full_analysis"] = result
    case_path = build_qa_case_from_analysis(result)
    st.session_state["current_qa_case_path"] = case_path
    if case_path:
        st.session_state["current_case_data"] = load_case_by_path(case_path)
    else:
        st.session_state["current_case_data"] = None
    st.success("Análisis completado. Caso guardado en data/qa_runs/.")


def _save_validation(case_path: str, score: int, feedback: str, verdict: str, adjustment: str) -> dict:
    return apply_validation(
        case_path,
        score=score,
        feedback=feedback or None,
        verdict=verdict,
        adjustment_decision=adjustment,
    )


def _select_case(path: str) -> None:
    st.session_state["selected_case_path"] = path
    st.session_state["current_qa_case_path"] = path
    st.session_state["current_case_data"] = load_case_by_path(path)


def main() -> None:
    st.set_page_config(page_title="RevMax Operator Console", layout="wide", initial_sidebar_state="collapsed")

    if "full_analysis" not in st.session_state:
        st.session_state["full_analysis"] = None
    if "current_qa_case_path" not in st.session_state:
        st.session_state["current_qa_case_path"] = None
    if "current_case_data" not in st.session_state:
        st.session_state["current_case_data"] = None
    if "selected_case_path" not in st.session_state:
        st.session_state["selected_case_path"] = None

    full = st.session_state["full_analysis"]
    report_data = get_report_display(full) if full else {}
    reasoning_data = get_reasoning_display(full) if full else {}
    case_path = st.session_state["current_qa_case_path"]
    case_data = st.session_state["current_case_data"]
    qa_cases = load_qa_cases(limit=100)
    qa_summary = get_qa_decision_summary()

    from layout import main_layout
    main_layout(
        on_run_analysis=_run_analysis,
        report_data=report_data,
        reasoning_data=reasoning_data,
        case_path=case_path,
        case_data=case_data,
        on_save_validation=_save_validation,
        qa_cases=qa_cases,
        on_select_case=_select_case,
        qa_summary=qa_summary,
    )


if __name__ == "__main__":
    main()
