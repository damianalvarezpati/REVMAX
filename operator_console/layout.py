"""
RevMax — Operator Console — Layout
===================================
Estructura de paneles de la consola.
"""

import streamlit as st
from typing import Any, Callable, Dict, List, Optional


def main_layout(
    on_run_analysis: Callable[[str, str, bool], None],
    report_data: Dict[str, Any],
    reasoning_data: Dict[str, Any],
    case_path: Optional[str],
    case_data: Optional[Dict],
    on_save_validation: Callable[[str, Optional[int], str, Optional[str], Optional[str]], dict],
    qa_cases: List[dict],
    on_select_case: Callable[[str], None],
    qa_summary: Dict[str, Any],
) -> None:
    """
    Distribución en 6 paneles con scroll vertical.
    Cada bloque en expander para mantener interfaz limpia.
    """
    st.title("RevMax — Operator Console")
    st.caption("Consola interna: generar análisis, revisar decisiones, validar casos, puntuar razonamiento.")

    # Panel 1 — Generar análisis
    from components import render_generate_panel
    render_generate_panel(on_run_analysis)

    st.divider()

    # Paneles 2 y 3 en dos columnas
    col_report, col_reason = st.columns(2)
    with col_report:
        from components import render_report_panel
        render_report_panel(report_data)
    with col_reason:
        from components import render_reasoning_panel
        render_reasoning_panel(reasoning_data)

    st.divider()

    # Panel 4 — Validación
    from components import render_validation_form
    current_score = case_data.get("human_score") if case_data else None
    current_verdict = case_data.get("human_verdict") if case_data else None
    current_feedback = case_data.get("human_feedback") if case_data else None
    current_adjustment = case_data.get("adjustment_decision") if case_data else None
    render_validation_form(
        case_path,
        current_score,
        current_verdict,
        current_feedback,
        current_adjustment,
        on_save_validation,
    )

    st.divider()

    # Panel 5 — Historial
    from components import render_case_history
    render_case_history(qa_cases, on_select_case)

    st.divider()

    # Panel 6 — Diagnóstico
    from components import render_model_diagnosis
    render_model_diagnosis(qa_summary)
