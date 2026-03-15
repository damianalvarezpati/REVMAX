"""
RevMax — QA Triage
==================
Taxonomía de issues y sugerencias de adjustment_decision para casos de validación.
Trabaja con los casos producidos por qa_case_builder sin modificar engines.
"""

from typing import Any, Dict, List, Optional

# Taxonomía mínima de issues
MISSED_CRITICAL_ALERT = "MISSED_CRITICAL_ALERT"
OVERREACTS_TO_WEAK_SIGNAL = "OVERREACTS_TO_WEAK_SIGNAL"
CONTRADICTORY_ACTION_AND_SCENARIO = "CONTRADICTORY_ACTION_AND_SCENARIO"
REPORT_NOT_ALIGNED_WITH_BRIEFING = "REPORT_NOT_ALIGNED_WITH_BRIEFING"
TOO_MUCH_NOISE = "TOO_MUCH_NOISE"
WEAK_EXECUTIVE_SUMMARY = "WEAK_EXECUTIVE_SUMMARY"
BAD_PRIORITY_RANKING = "BAD_PRIORITY_RANKING"
UNCLEAR_STRATEGY = "UNCLEAR_STRATEGY"
MEMORY_NOT_USEFUL = "MEMORY_NOT_USEFUL"
CHANGE_DETECTION_NOT_USEFUL = "CHANGE_DETECTION_NOT_USEFUL"
CASE_NOT_EXPLAINABLE = "CASE_NOT_EXPLAINABLE"

ISSUE_LABELS = {
    MISSED_CRITICAL_ALERT: "Sistema no detectó o no priorizó una alerta crítica",
    OVERREACTS_TO_WEAK_SIGNAL: "Sistema reacciona de más a una señal débil",
    CONTRADICTORY_ACTION_AND_SCENARIO: "Acción recomendada y escenario no son coherentes",
    REPORT_NOT_ALIGNED_WITH_BRIEFING: "Informe no alineado con el briefing consolidado",
    TOO_MUCH_NOISE: "Demasiado ruido o detalle que no aporta",
    WEAK_EXECUTIVE_SUMMARY: "Resumen ejecutivo débil o poco accionable",
    BAD_PRIORITY_RANKING: "Orden de prioridad de acciones/oportunidades incorrecto",
    UNCLEAR_STRATEGY: "Estrategia (DEFENSIVE/AGGRESSIVE/PREMIUM/BALANCED) poco clara",
    MEMORY_NOT_USEFUL: "Memoria / comparación con corrida anterior no útil",
    CHANGE_DETECTION_NOT_USEFUL: "Detección de cambios no útil o confusa",
    CASE_NOT_EXPLAINABLE: "Caso no explicable: por qué esta conclusión no queda claro",
}

# Sugerencias de adjustment_decision
ADJUST_THRESHOLDS = "adjust_thresholds"
ADJUST_WEIGHTS = "adjust_weights"
REVIEW_PROMPT_STRUCTURE = "review_prompt_structure"
REVIEW_ACTION_RULES = "review_action_rules"
REVIEW_STRATEGY_RULES = "review_strategy_rules"
NO_CHANGE_NEEDED = "no_change_needed"

ADJUSTMENT_LABELS = {
    ADJUST_THRESHOLDS: "Ajustar umbrales (alertas, señales, scoring)",
    ADJUST_WEIGHTS: "Ajustar pesos (confianza, priorización)",
    REVIEW_PROMPT_STRUCTURE: "Revisar estructura de prompts (report agent)",
    REVIEW_ACTION_RULES: "Revisar reglas de acciones recomendadas",
    REVIEW_STRATEGY_RULES: "Revisar reglas del strategy engine",
    NO_CHANGE_NEEDED: "No cambiar nada; caso correcto o no aplicable",
}


def suggest_adjustment_for_issue(issue: str) -> List[str]:
    """
    Sugiere una lista de adjustment_decision recomendados para un issue.
    """
    mapping = {
        MISSED_CRITICAL_ALERT: [ADJUST_THRESHOLDS, REVIEW_ACTION_RULES],
        OVERREACTS_TO_WEAK_SIGNAL: [ADJUST_THRESHOLDS, ADJUST_WEIGHTS],
        CONTRADICTORY_ACTION_AND_SCENARIO: [REVIEW_STRATEGY_RULES, REVIEW_ACTION_RULES],
        REPORT_NOT_ALIGNED_WITH_BRIEFING: [REVIEW_PROMPT_STRUCTURE],
        TOO_MUCH_NOISE: [REVIEW_PROMPT_STRUCTURE, ADJUST_THRESHOLDS],
        WEAK_EXECUTIVE_SUMMARY: [REVIEW_PROMPT_STRUCTURE],
        BAD_PRIORITY_RANKING: [ADJUST_WEIGHTS, REVIEW_ACTION_RULES],
        UNCLEAR_STRATEGY: [REVIEW_STRATEGY_RULES],
        MEMORY_NOT_USEFUL: [ADJUST_THRESHOLDS, REVIEW_PROMPT_STRUCTURE],
        CHANGE_DETECTION_NOT_USEFUL: [ADJUST_THRESHOLDS],
        CASE_NOT_EXPLAINABLE: [REVIEW_PROMPT_STRUCTURE, ADJUST_WEIGHTS],
    }
    return mapping.get(issue, [NO_CHANGE_NEEDED])


def triage_case(case: dict) -> Dict[str, Any]:
    """
    Analiza un caso de validación y devuelve:
    - issues_detected: lista de códigos de issue que podrían aplicarse (heurístico)
    - suggested_adjustments: lista de adjustment_decision sugeridos
    - explainability_ok: bool indicando si why_this_conclusion está presente y no vacío
    No modifica el caso.
    """
    issues = []
    signals = case.get("interpreted_signals") or {}
    verdict = case.get("system_verdict") or {}
    actions = case.get("recommended_actions") or []
    scenario = (case.get("recommended_scenario") or "").lower()
    why = case.get("why_this_conclusion") or {}
    if isinstance(why, list):
        why = {}
    top_risks = case.get("top_risks") or []
    observed = case.get("observed_facts") or {}

    action_postures = set()
    for a in actions:
        if isinstance(a, dict):
            hint = (a.get("action_hint") or "").lower()
            if "raise" in hint or "subir" in hint:
                action_postures.add("raise")
            elif "lower" in hint or "bajar" in hint:
                action_postures.add("lower")
            elif "hold" in hint or "mantener" in hint or "paridad" in hint:
                action_postures.add("hold")
    if action_postures and scenario and scenario not in action_postures and len(action_postures) > 1:
        issues.append(CONTRADICTORY_ACTION_AND_SCENARIO)

    critical_alerts = [r for r in top_risks if isinstance(r, dict) and r.get("severity") == "critical"]
    if observed.get("alert_types"):
        has_critical = any("CRITICAL" in (t or "").upper() or "PARITY" in (t or "").upper() for t in observed.get("alert_types", []))
        if has_critical and not critical_alerts and not actions:
            issues.append(MISSED_CRITICAL_ALERT)

    strategy = signals.get("strategy_label") or ""
    if not strategy or strategy not in ("DEFENSIVE", "AGGRESSIVE", "PREMIUM", "BALANCED"):
        issues.append(UNCLEAR_STRATEGY)

    why_text = why.get("why_recommended_scenario_defendable") if isinstance(why, dict) else None
    if not why_text or (isinstance(why_text, str) and len(why_text.strip()) < 20):
        issues.append(CASE_NOT_EXPLAINABLE)

    drivers = why.get("main_drivers") if isinstance(why, dict) else []
    if not drivers and not why_text:
        issues.append(CASE_NOT_EXPLAINABLE)

    suggested = []
    for issue in issues:
        for adj in suggest_adjustment_for_issue(issue):
            if adj not in suggested:
                suggested.append(adj)
    if not suggested:
        suggested.append(NO_CHANGE_NEEDED)

    explainability_ok = bool(why_text and len(str(why_text).strip()) >= 20)

    return {
        "issues_detected": issues,
        "issues_labels": [ISSUE_LABELS.get(i, i) for i in issues],
        "suggested_adjustments": suggested,
        "adjustment_labels": [ADJUSTMENT_LABELS.get(a, a) for a in suggested],
        "explainability_ok": explainability_ok,
    }


def get_all_issue_codes() -> List[str]:
    """Devuelve todos los códigos de issue de la taxonomía."""
    return [
        MISSED_CRITICAL_ALERT,
        OVERREACTS_TO_WEAK_SIGNAL,
        CONTRADICTORY_ACTION_AND_SCENARIO,
        REPORT_NOT_ALIGNED_WITH_BRIEFING,
        TOO_MUCH_NOISE,
        WEAK_EXECUTIVE_SUMMARY,
        BAD_PRIORITY_RANKING,
        UNCLEAR_STRATEGY,
        MEMORY_NOT_USEFUL,
        CHANGE_DETECTION_NOT_USEFUL,
        CASE_NOT_EXPLAINABLE,
    ]


def get_all_adjustment_codes() -> List[str]:
    """Devuelve todos los códigos de adjustment_decision."""
    return [
        ADJUST_THRESHOLDS,
        ADJUST_WEIGHTS,
        REVIEW_PROMPT_STRUCTURE,
        REVIEW_ACTION_RULES,
        REVIEW_STRATEGY_RULES,
        NO_CHANGE_NEEDED,
    ]
