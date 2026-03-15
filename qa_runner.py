"""
RevMax — QA Runner
==================
Punto de entrada para construir y registrar casos de validación.
Usa qa_case_builder + qa_registry. No toca analysis_runner ni job engine.
"""

import os
from typing import Optional

from qa_case_builder import build_validation_case_from_briefing
from qa_registry import (
    save_validation_case,
    load_validation_cases,
    summarize_validation_cases,
    build_qa_decision_summary,
)


def run_qa_from_briefing(
    briefing: dict,
    hotel_name: str,
    scenario_name: Optional[str] = None,
    base_dir: Optional[str] = None,
) -> dict:
    """
    Construye un caso de validación desde el briefing y lo guarda en data/qa_runs/.
    Devuelve el caso con la clave "_saved_path" añadida.
    """
    case = build_validation_case_from_briefing(briefing, hotel_name, scenario_name=scenario_name)
    path = save_validation_case(case, base_dir=base_dir)
    case["_saved_path"] = path
    return case


def run_qa_from_full_analysis(
    full_analysis: dict,
    scenario_name: Optional[str] = None,
    base_dir: Optional[str] = None,
) -> dict:
    """
    Extrae briefing y hotel_name de full_analysis (resultado del orquestador)
    y ejecuta run_qa_from_briefing.
    """
    briefing = full_analysis.get("briefing") or {}
    hotel_name = full_analysis.get("hotel_name") or "Unknown"
    return run_qa_from_briefing(briefing, hotel_name, scenario_name=scenario_name, base_dir=base_dir)
