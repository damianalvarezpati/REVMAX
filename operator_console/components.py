"""
RevMax — Operator Console — Components
=======================================
Componentes reutilizables para la consola Streamlit.
"""

import streamlit as st
from typing import Any, Dict, List, Optional


def render_generate_panel(on_run: callable) -> None:
    """Panel 1: Hotel, fecha, botón RUN ANALYSIS."""
    with st.expander("Generar análisis", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            hotel = st.text_input("Hotel name", value="", key="op_hotel")
        with col2:
            city = st.text_input("Ciudad (opcional)", value="", key="op_city")
        fast_demo = st.checkbox("Demo rápido (sin scraping)", value=True, key="op_fast_demo")
        if st.button("RUN ANALYSIS", type="primary", key="op_run"):
            if not (hotel or "").strip():
                st.error("Indica el nombre del hotel.")
            else:
                on_run(hotel.strip(), city.strip(), fast_demo)


def render_report_panel(data: Dict[str, Any]) -> None:
    """Panel 2: Informe — executive summary, strategy, risks, actions, opportunities, scenario, change."""
    if not data:
        st.info("Ejecuta un análisis para ver el informe.")
        return
    with st.expander("Informe", expanded=True):
        st.markdown("**Estado**")
        st.caption(data.get("overall_status", "—"))
        st.markdown("---")
        st.markdown("**Resumen ejecutivo**")
        st.markdown(data.get("executive_summary", "—") or "—")
        st.markdown("---")
        st.markdown("**Estrategia**")
        st.markdown(f"{data.get('strategy', '—')} — {data.get('strategy_rationale', '')}")
        st.markdown("---")
        st.markdown("**Top risks**")
        for line in data.get("top_risks") or []:
            st.markdown(line)
        if not data.get("top_risks"):
            st.caption("Ninguno")
        st.markdown("---")
        st.markdown("**Acciones recomendadas**")
        for line in data.get("recommended_actions") or []:
            st.markdown(line)
        if not data.get("recommended_actions"):
            st.caption("Ninguna")
        st.markdown("---")
        st.markdown("**Oportunidades**")
        for line in data.get("top_opportunities") or []:
            st.markdown(line)
        if not data.get("top_opportunities"):
            st.caption("Ninguna")
        st.markdown("---")
        st.markdown("**Escenario recomendado**")
        st.markdown(f"{data.get('scenario_recommendation', '—')} — {data.get('scenario_summary', '')}")
        st.markdown("---")
        st.markdown("**Change detection**")
        st.markdown(f"Resumen: {data.get('change_summary', '—')} | Severidad: {data.get('change_severity', '—')}")
        for h in data.get("change_highlights") or []:
            st.markdown(f"• {h}")


def render_reasoning_panel(data: Dict[str, Any]) -> None:
    """Panel 3: Razonamiento — observed facts, interpreted signals, value, scenario, change."""
    if not data:
        st.info("Ejecuta un análisis para ver el razonamiento.")
        return
    with st.expander("Razonamiento del sistema", expanded=True):
        obs = data.get("observed_facts") or {}
        st.markdown("**OBSERVED FACTS**")
        st.caption(f"Demand score: {obs.get('demand_score', '—')} | Signal: {obs.get('demand_signal', '—')}")
        st.caption(f"Ranking: #{obs.get('pricing_position_rank', '—')} / {obs.get('pricing_total_compset', '—')}")
        st.caption(f"GRI: {obs.get('reputation_gri', '—')} | Parity: {obs.get('parity_status', '—')} | Visibility: {obs.get('visibility', '—')}")
        if obs.get("alert_types"):
            st.caption(f"Alertas: {', '.join(obs.get('alert_types', []))}")
        if obs.get("market_signal_types"):
            st.caption(f"Señales mercado: {', '.join(obs.get('market_signal_types', []))}")
        if obs.get("pickup_signal"):
            st.caption("Pickup: sí")
        if obs.get("compression_signal"):
            st.caption("Compression: sí")
        st.markdown("---")
        interp = data.get("interpreted_signals") or {}
        st.markdown("**INTERPRETED SIGNALS**")
        st.caption(f"strategy_label: {interp.get('strategy_label', '—')}")
        st.caption(f"overall_status: {interp.get('derived_overall_status', '—')}")
        st.caption(f"consolidated_price_action: {interp.get('consolidated_price_action', '—')}")
        st.caption(f"recommended_scenario: {interp.get('recommended_scenario', '—')}")
        st.caption(f"top_priority_item: {interp.get('top_priority_item', '—')}")
        st.markdown("---")
        st.markdown("**VALUE PRIORITIZATION**")
        st.caption(data.get("value_summary", "—"))
        top = data.get("top_priority_item")
        if isinstance(top, dict):
            st.caption(f"Top: {top.get('title', top.get('type', '?'))} — score {top.get('priority_score', '?')}")
        st.markdown("---")
        st.markdown("**SCENARIO ANALYSIS**")
        for s in data.get("scenario_analysis") or []:
            st.caption(f"{s.get('scenario', '?')}: support={s.get('support')} risk={s.get('risk')} net={s.get('net')}")
        if not data.get("scenario_analysis"):
            st.caption("—")
        st.markdown("---")
        st.markdown("**CHANGE DETECTION**")
        st.caption(f"Summary: {data.get('change_summary', '—')} | Severity: {data.get('change_severity', '—')}")
        for h in data.get("change_highlights") or []:
            st.caption(f"• {h}")


def render_validation_form(
    case_path: Optional[str],
    current_score: Optional[int],
    current_verdict: Optional[str],
    current_feedback: Optional[str],
    current_adjustment: Optional[str],
    on_save: callable,
) -> None:
    """Panel 4: Formulario de validación humana."""
    with st.expander("Validación humana", expanded=True):
        if not case_path:
            st.warning("Ejecuta un análisis para generar un caso y validarlo.")
            return
        score = st.radio("Score reasoning quality", [1, 2, 3, 4, 5], index=[1, 2, 3, 4, 5].index(current_score) if current_score in [1, 2, 3, 4, 5] else 2, key="op_score", horizontal=True)
        verdict = st.selectbox(
            "Agreement",
            ["agree", "partial", "disagree"],
            index=["agree", "partial", "disagree"].index(current_verdict) if current_verdict in ("agree", "partial", "disagree") else 0,
            key="op_verdict",
        )
        feedback = st.text_area("Feedback text", value=current_feedback or "", key="op_feedback", height=80)
        adj_opts = ["adjust_thresholds", "adjust_weights", "review_prompt_structure", "review_action_rules", "review_strategy_rules", "no_change_needed"]
        adj_idx = adj_opts.index(current_adjustment) if current_adjustment in adj_opts else 5
        adjustment = st.selectbox("Adjustment decision", adj_opts, index=adj_idx, key="op_adjustment")
        if st.button("SAVE VALIDATION", key="op_save_val"):
            result = on_save(case_path, score, feedback.strip(), verdict, adjustment)
            if result.get("error"):
                st.error(result["error"])
            else:
                st.success("Validación guardada.")


def render_case_history(cases: List[dict], on_select: callable) -> None:
    """Panel 5: Tabla de casos en data/qa_runs/."""
    with st.expander("Historial de casos", expanded=False):
        if not cases:
            st.caption("No hay casos en data/qa_runs/.")
            return
        for idx, c in enumerate(cases[:30]):
            path = c.get("_path", "")
            ts = (c.get("timestamp") or "")[:19]
            hotel = c.get("hotel_name", "—")
            score = c.get("human_score", "—")
            verdict = c.get("human_verdict", "—")
            adj = c.get("adjustment_decision", "—")
            if st.button(f"{ts} | {hotel} | {score} | {verdict} | {adj}", key=f"hist_{idx}", use_container_width=True):
                on_select(path)


def render_model_diagnosis(summary: Dict[str, Any]) -> None:
    """Panel 6: build_qa_decision_summary — media score, % verdicts, issues, next adjustment."""
    with st.expander("Diagnóstico del modelo", expanded=False):
        if not summary or summary.get("total_cases", 0) == 0:
            st.caption("No hay casos con validación para resumir.")
            return
        st.metric("Total casos", summary.get("total_cases", 0))
        st.metric("Average score", summary.get("human_score_mean") or "—")
        v = summary.get("human_verdict_pct") or {}
        st.caption(f"Agree: {v.get('agree', 0)}% | Partial: {v.get('partial', 0)}% | Disagree: {v.get('disagree', 0)}%")
        st.markdown("**Most common issues**")
        for i in summary.get("most_common_issues") or []:
            st.caption(f"• {i.get('label', i.get('issue', '?'))} ({i.get('count', 0)})")
        rec = summary.get("recommended_next_adjustment")
        if rec:
            st.markdown("**Recommended next adjustment**")
            st.caption(f"{rec.get('label', rec.get('code', '?'))} ({rec.get('count', 0)})")
