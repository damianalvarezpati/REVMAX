"""
RevMax — Agente 7: Report Writer
==================================
Director de Comunicación Ejecutiva Hotelera
Metodología: Cornell Hotel School · McKinsey Pyramid Principle · STR reporting

Este agente recibe los outputs de los 6 agentes anteriores y los convierte
en el informe diario que recibirá el director del hotel. El informe debe ser
el mejor revenue manager virtual que el director haya tenido.
"""

AGENT_SYSTEM_PROMPT = """
Eres el redactor del informe diario de RevMax para el director del hotel o el revenue manager.
El informe debe responder de forma muy clara a una sola pregunta:

  ¿Mi precio actual está bien o qué debería hacer y por qué?

TONO OBLIGATORIO: humano, cercano, profesional, claro, elegante, directo pero no brusco.
Escribe como un revenue manager con criterio que habla a un par, no como un sistema técnico.

PROHIBIDO (nunca uses estas fórmulas):
  - "Market indicates hold" / "Market suggests lower" / "Strategy adequate"
  - "Recommended posture: hold" / "Pricing strategy appropriate"
  - "Signals are mixed" sin explicar qué señales y qué implican
  - "Tu estrategia es incorrecta" / "Te equivocas"
  - Frases vagas o robóticas que no explican la lógica de negocio

SÍ USA (ejemplos de estilo deseado):
  - "Tu precio actual está por debajo del mercado y sugiere una estrategia orientada a captar demanda."
  - "Este enfoque suele funcionar bien cuando la demanda es baja o incierta."
  - "Sin embargo, en este momento el mercado en tu zona muestra señales de demanda fuerte."
  - "En este contexto, podría existir margen para aumentar el precio sin comprometer la ocupación."
  - "Tu precio actual sugiere una estrategia agresiva, que suele funcionar bien en contextos de demanda débil."

ESTRUCTURA OBLIGATORIA DEL report_text (en este orden, con párrafos separados por \\n\\n):

1. RECOMENDACIÓN
   Una frase muy clara: "Subir ligeramente el precio" / "Mantener el precio actual" / "Revisar a la baja el precio actual".

2. CONTEXTO DE MERCADO
   Demanda detectada, eventos relevantes (si hay eventos concretos, enuméralos por nombre; si no hay nombres fiables, di: "Se han detectado señales de demanda elevada, aunque no ha sido posible identificar con precisión los eventos causantes."), situación de la competencia.

3. POSICIÓN DEL HOTEL
   Precio del hotel frente al compset: por debajo / alineado / por encima. Si competidores venden más caro o más barato, dilo con naturalidad.

4. INTERPRETACIÓN ESTRATÉGICA
   Qué estrategia parece reflejar el precio actual (captación de demanda / equilibrada / premium) y por qué tiene sentido o no en el contexto actual. Si hay disonancia (ej. precio bajo + demanda alta), explícala sin acusar: "Esto podría indicar margen para una estrategia ligeramente más firme."

5. ACCIÓN SUGERIDA
   Recomendación clara, breve y práctica para cerrar.

PARIDAD: No escribas "La paridad es correcta." Usa frases explicativas:
  - "No se han detectado discrepancias relevantes entre los principales canales revisados."
  - "La tarifa parece consistente entre los portales analizados."
  - "Se han observado diferencias entre canales, lo que puede afectar a la competitividad."
Si conoces el número de canales revisados, puedes mencionarlo. Si no, no lo inventes.

BOOKING / POSICIÓN EN PORTALES: No uses la posición como argumento fuerte sin contexto. Si el dato no es fiable o no está segmentado, no bases la recomendación en él. Si lo usas, explícalo con prudencia.

CONFIANZA: Si la confianza del análisis es baja, dilo de forma elegante en el informe, por ejemplo:
  - "Esta recomendación debe interpretarse con prudencia, ya que la calidad de los datos disponibles en esta corrida ha sido limitada."
  - "El análisis apunta en esta dirección, aunque la confianza es moderada por falta de algunos datos clave."
No pongas un porcentaje suelto sin contexto.

REGLAS: Máximo 400 palabras en report_text. Máximo 3 priority_actions. Asunto del email <60 caracteres. Nunca inventes datos. Usa el nombre del hotel.
"""

import json
import re
import asyncio
import os
import sys
from typing import Optional

from anthropic import AsyncAnthropic
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_REPORT_DEBUG_LOG = "report_agent_debug.log"
_MAX_RAW_LOG_CHARS = 2000


def _report_debug_path() -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "data", _REPORT_DEBUG_LOG)


def _log_report_failure(
    prompt_len: int,
    response_len: int,
    raw_preview: str,
    parse_error: str,
) -> None:
    try:
        log_path = _report_debug_path()
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(
                f"\n[{datetime.utcnow().isoformat()}Z] "
                f"prompt_len={prompt_len} response_len={response_len}\n"
                f"parse_error: {parse_error}\n"
                f"raw_preview:\n{raw_preview}\n"
            )
            f.flush()
    except Exception:
        pass


def _build_minimal_report_from_analysis(full_analysis: dict) -> dict:
    """
    Informe mínimo válido generado por código cuando el LLM falla o devuelve JSON inválido.
    Siempre devuelve un dict con todas las claves que espera el mailer y el pipeline.
    """
    hotel_name = full_analysis.get("hotel_name", "el hotel")
    briefing = full_analysis.get("briefing", {})
    derived = (briefing.get("derived_overall_status") or "stable").lower()
    action = (briefing.get("consolidated_price_action") or "hold").upper()
    seed = briefing.get("recommended_priority_actions_seed") or []
    actions = []
    for i, s in enumerate(seed[:3], 1):
        if isinstance(s, dict):
            actions.append({
                "rank": i,
                "urgency": s.get("urgency", "this_week"),
                "action": s.get("action_hint", s.get("reason_source", "Revisar postura"))[:200],
                "room_type": "general",
                "metric": "",
                "reason": s.get("reason_source", "consolidación"),
                "expected_impact": "",
            })
        else:
            actions.append({
                "rank": i,
                "urgency": "this_week",
                "action": str(s)[:200],
                "room_type": "general",
                "metric": "",
                "reason": "Sistema",
                "expected_impact": "",
            })
    if not actions:
        actions = [{
            "rank": 1,
            "urgency": "this_week",
            "action": f"Mantener postura {action} según consolidación.",
            "room_type": "general",
            "metric": "",
            "reason": "Decisión consolidada",
            "expected_impact": "",
        }]
    status_summary = f"Postura {action}. Estado derivado: {derived}."
    report_text = (
        f"Resumen ejecutivo (informe mínimo generado por sistema).\n\n"
        f"Estado: {derived.upper()}. Acción consolidada: {action}.\n\n"
        f"{status_summary}\n\n"
        f"Acciones recomendadas: ver lista inferior. RevMax recomienda vigilar demanda y posición de precio esta semana."
    )
    return {
        "email_subject": f"RevMax · {hotel_name} · {datetime.now().strftime('%d %b')}",
        "overall_status": derived if derived in ("strong", "stable", "needs_attention", "alert") else "stable",
        "status_summary": status_summary,
        "report_text": report_text,
        "priority_actions": actions,
        "weekly_watchlist": "Vigilar demanda y posición vs compset esta semana.",
    }


def _parse_report_response(raw: str, full_analysis: dict) -> tuple:
    """
    Parsea la respuesta del LLM. Nunca lanza: si todo falla devuelve (informe_mínimo, True).
    Orden: json.loads(raw) -> regex extract + json.loads -> fallback mínimo.
    Devuelve (dict, used_fallback: bool).
    """
    raw = (raw or "").strip()
    parse_error = "unknown"

    try:
        result = json.loads(raw)
        if isinstance(result, dict) and result.get("report_text") is not None:
            return _normalize_report_dict(result, full_analysis), False
        parse_error = "JSON root is not a dict or missing report_text"
    except json.JSONDecodeError as e:
        parse_error = str(e)
    except Exception as e:
        parse_error = f"unexpected: {e}"

    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        try:
            result = json.loads(match.group(0))
            if isinstance(result, dict) and result.get("report_text") is not None:
                return _normalize_report_dict(result, full_analysis), False
        except json.JSONDecodeError as e2:
            parse_error = f"{parse_error}; regex_block: {e2}"
        except Exception as e2:
            parse_error = f"{parse_error}; regex_block: {e2}"

    return _build_minimal_report_from_analysis(full_analysis), True


def _normalize_report_dict(result: dict, full_analysis: dict) -> dict:
    """Asegura que el dict tenga todas las claves requeridas; rellena con mínimo si falta."""
    hotel_name = full_analysis.get("hotel_name", "el hotel")
    minimal = _build_minimal_report_from_analysis(full_analysis)
    out = dict(minimal)
    out.update({k: v for k, v in result.items() if v is not None})
    if not out.get("status_summary"):
        out["status_summary"] = (result.get("report_text") or "")[:120] or minimal["status_summary"]
    if not out.get("weekly_watchlist"):
        out["weekly_watchlist"] = minimal["weekly_watchlist"]
    if not isinstance(out.get("priority_actions"), list):
        out["priority_actions"] = minimal["priority_actions"]
    for a in out.get("priority_actions") or []:
        if isinstance(a, dict):
            a.setdefault("rank", 0)
            a.setdefault("urgency", "this_week")
            a.setdefault("action", "")
            a.setdefault("reason", "")
            a.setdefault("expected_impact", "")
    return out


async def run_report_agent(
    full_analysis: dict,
    api_key: str,
    model: str = "claude-opus-4-5",
    debug_dir: Optional[str] = None,
) -> dict:
    """
    Recibe el análisis completo del orquestador y genera el informe.
    Siempre devuelve un dict válido (éxito, parse parcial o fallback mínimo).
    Nunca lanza por JSON inválido o truncado.
    Si debug_dir está definido, guarda report_prompt, report_raw y report_normalized.
    """
    client = AsyncAnthropic(api_key=api_key)
    user_prompt = _build_report_prompt(full_analysis)
    prompt_len = len(user_prompt)
    if debug_dir:
        try:
            from debug_runs import save_debug_artifact
            save_debug_artifact(debug_dir, "report_prompt", user_prompt, as_json=False)
        except Exception:
            pass

    hotel_name = full_analysis.get("hotel_name", "el hotel")
    print(f"  [Agente Report] Redactando informe ejecutivo para {hotel_name}... (prompt_len={prompt_len})", flush=True)

    raw = ""
    response_len = 0
    parse_error_log = None

    try:
        response = await client.messages.create(
            model=model,
            max_tokens=2048,
            system=AGENT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = (response.content[0].text if response.content else "") or ""
        raw = raw.strip()
        response_len = len(raw)
        if debug_dir and raw:
            try:
                from debug_runs import save_debug_artifact
                save_debug_artifact(debug_dir, "report_raw", raw, as_json=False)
            except Exception:
                pass
    except Exception as e:
        parse_error_log = f"API exception: {e}"
        _log_report_failure(
            prompt_len,
            response_len,
            (raw or "")[:_MAX_RAW_LOG_CHARS],
            parse_error_log,
        )
        return _build_minimal_report_from_analysis(full_analysis)

    if not raw:
        parse_error_log = "empty response"
        _log_report_failure(prompt_len, response_len, "", parse_error_log)
        return _build_minimal_report_from_analysis(full_analysis)

    try:
        result, used_fallback = _parse_report_response(raw, full_analysis)
    except Exception as e:
        _log_report_failure(
            prompt_len,
            response_len,
            raw[:_MAX_RAW_LOG_CHARS],
            f"parse raised: {e}",
        )
        return _build_minimal_report_from_analysis(full_analysis)

    if used_fallback:
        _log_report_failure(
            prompt_len,
            response_len,
            raw[:_MAX_RAW_LOG_CHARS],
            "parse failed; returned minimal report",
        )

    if debug_dir:
        try:
            from debug_runs import save_debug_artifact
            save_debug_artifact(debug_dir, "report_normalized", result, as_json=True)
        except Exception:
            pass
    print(f"  [Agente Report] OK Informe generado — asunto: {(result.get('email_subject') or '?')[:60]} response_len={response_len}", flush=True)
    return result


def _normalize_list_of_strings(lst, max_len: int = 80) -> list:
    """Convierte cada elemento a string para el prompt; dicts/non-strings no rompen."""
    out = []
    for i, x in enumerate(lst):
        if x is None:
            continue
        if isinstance(x, str):
            out.append(x[:max_len] if len(x) > max_len else x)
        elif isinstance(x, dict):
            out.append(json.dumps(x, ensure_ascii=False)[:max_len])
        else:
            out.append(str(x)[:max_len])
    return out


def _normalize_list_of_dicts(lst, keys: list) -> list:
    """Filtra solo dicts y extrae claves; evita .get() sobre no-dicts."""
    out = []
    for x in lst:
        if not isinstance(x, dict):
            continue
        out.append({k: (x.get(k) if isinstance(x.get(k), (str, int, float, bool, type(None))) else str(x.get(k))[:100]) for k in keys})
    return out


def _format_events_for_report(events: list) -> str:
    """
    Formatea eventos para el informe. Si hay nombres concretos, los enumera.
    Si no hay nombres fiables, devuelve mensaje de señales sin identificar.
    """
    if not events:
        return ""
    names = []
    for e in events:
        if isinstance(e, str) and e.strip():
            names.append(e.strip())
        elif isinstance(e, dict) and (e.get("name") or e.get("title") or e.get("event_name")):
            names.append((e.get("name") or e.get("title") or e.get("event_name") or "").strip())
    if names:
        return "Eventos detectados: " + ", ".join(names[:8])
    return "Se han detectado señales de demanda elevada, aunque no ha sido posible identificar con precisión los eventos causantes."


def _infer_price_positioning_language(outputs: dict) -> tuple:
    """
    Infiere la posición del precio (por debajo / alineado / por encima) y la estrategia implícita.
    Devuelve (frase_posición, estrategia_implícita).
    """
    discovery = outputs.get("discovery", {})
    compset = outputs.get("compset", {})
    compset_summary = compset.get("compset_summary") or {}
    try:
        own = discovery.get("adr_double")
        market = compset_summary.get("primary_avg_adr")
        if own is not None and market is not None and isinstance(own, (int, float)) and isinstance(market, (int, float)) and market > 0:
            diff_pct = (own - market) / market
            if diff_pct <= -0.05:
                return (
                    "Tu precio actual está por debajo de la media del compset.",
                    "agresiva / orientada a captar demanda",
                )
            if diff_pct >= 0.05:
                return (
                    "Tu precio actual está por encima de la media del compset.",
                    "premium / de maximización de ADR",
                )
            return (
                "Tu precio actual está alineado con la media del compset.",
                "equilibrada",
            )
    except (TypeError, ZeroDivisionError):
        pass
    return ("", "")


def _build_human_strategy_message(
    briefing: dict,
    outputs: dict,
    positioning_phrase: str,
    strategy_label: str,
) -> str:
    """
    Construye un mensaje humano que cruza la estrategia implícita del precio con el contexto real.
    No acusatorio; sugiere disonancia o alineación con frases tipo "podría existir margen" / "suele funcionar bien cuando...".
    """
    if not positioning_phrase:
        return ""
    demand = outputs.get("demand", {})
    raw_signal = (demand.get("demand_index") or {}).get("signal", "medium") or "medium"
    demand_signal = str(raw_signal).lower().replace(" ", "_") if raw_signal else "medium"
    action = (briefing.get("consolidated_price_action") or "hold").lower()
    parts = []
    if "por debajo" in positioning_phrase:
        parts.append("Tu precio actual sugiere una estrategia orientada a captar demanda. Este enfoque suele funcionar bien cuando la demanda es baja o incierta.")
        if demand_signal in ("high", "very_high") and action in ("raise", "hold"):
            parts.append("Sin embargo, en este momento el mercado muestra señales de demanda fuerte. Varios competidores podrían estar vendiendo más caro para fechas similares. En este contexto, podría existir margen para aumentar el precio sin comprometer la ocupación.")
        elif demand_signal in ("low", "very_low"):
            parts.append("En el contexto actual de demanda débil, esta postura es coherente con el mercado.")
    elif "por encima" in positioning_phrase:
        parts.append("Tu precio actual refleja una estrategia premium o de maximización de ADR.")
        if demand_signal in ("low", "very_low") and action in ("lower", "hold"):
            parts.append("Con demanda actualmente baja, conviene vigilar la ocupación; si esta se resiente, podría ser momento de revisar a la baja de forma selectiva.")
        else:
            parts.append("Si la reputación y la demanda lo sostienen, tiene sentido mantener una postura firme.")
    else:
        parts.append("Tu precio está alineado con el mercado, lo que refleja una estrategia equilibrada.")
        if action == "raise":
            parts.append("Las señales actuales apuntan a que podría haber margen para una subida moderada.")
        elif action == "lower":
            parts.append("Las señales sugieren revisar a la baja en algún segmento o fecha.")
    return " ".join(parts)


def _build_human_confidence_message(system_confidence: float) -> str:
    """
    Si la confianza es baja, devuelve una frase elegante para que el informe la use.
    Si es aceptable, devuelve cadena vacía.
    """
    if system_confidence is None:
        return ""
    try:
        c = float(system_confidence)
    except (TypeError, ValueError):
        return ""
    if c < 0.5:
        return "Esta recomendación debe interpretarse con prudencia, ya que la calidad de los datos disponibles en esta corrida ha sido limitada."
    if c < 0.65:
        return "El análisis apunta en esta dirección, aunque la confianza es moderada por falta de algunos datos clave."
    return ""


def _build_parity_message(parity_status: str, channels_mentioned: bool = False) -> str:
    """
    Mensaje humano sobre paridad entre canales. Evita "La paridad es correcta."
    """
    if not parity_status or parity_status == "ok":
        if channels_mentioned:
            return "No se han detectado discrepancias relevantes entre los principales canales revisados."
        return "La tarifa parece consistente entre los portales analizados."
    if str(parity_status).lower() in ("violation", "violación", "error"):
        return "Se han observado diferencias entre canales, lo que puede afectar a la competitividad o a la conversión."
    return "Revisión de paridad: " + str(parity_status)


def _build_report_prompt(full_analysis: dict) -> str:
    hotel_name = full_analysis.get("hotel_name", "?")
    date = full_analysis.get("analysis_date", datetime.now().strftime("%Y-%m-%d"))
    briefing = full_analysis.get("briefing", {})
    outputs = full_analysis.get("agent_outputs", {})

    discovery = outputs.get("discovery", {})
    compset = outputs.get("compset", {})
    pricing = outputs.get("pricing", {})
    demand = outputs.get("demand", {})
    reputation = outputs.get("reputation", {})
    distribution = outputs.get("distribution", {})

    # Extraer datos clave de cada agente
    your_adr = discovery.get("adr_double", "?")
    market_avg = compset.get("compset_summary", {}).get("primary_avg_adr", "?")
    your_rank = pricing.get("market_context", {}).get("your_position_rank", "?")
    total_compset = pricing.get("market_context", {}).get("total_compset", "?")
    ari = pricing.get("indices", {}).get("ari", {}).get("value", "?")
    rgi = pricing.get("indices", {}).get("rgi", {}).get("value", "?")
    quadrant = pricing.get("position_diagnosis", {}).get("quadrant", "?")
    price_action = pricing.get("recommendation", {}).get("action", "?")
    price_primary = pricing.get("recommendation", {}).get("primary_action", "")

    demand_score = demand.get("demand_index", {}).get("score", "?")
    demand_signal = demand.get("demand_index", {}).get("signal", "?")
    events = demand.get("events_detected", [])
    forecast_7d = demand.get("forecast", {}).get("next_7_days", {})

    gri = reputation.get("gri", {}).get("value", "?")
    gri_vs_compset = reputation.get("gri", {}).get("vs_compset_avg", "?")
    neg_themes = reputation.get("recent_negative_themes", [])
    price_perception = reputation.get("sentiment_analysis", {}).get("price_perception", "?")

    visibility = distribution.get("visibility_score", "?")
    booking_pos = distribution.get("booking_audit", {}).get("search_position", "?")
    parity_status = distribution.get("rate_parity", {}).get("status", "ok")
    quick_wins = distribution.get("quick_wins", [])

    # Conflictos y decisión consolidada
    conflicts = briefing.get("conflicts", [])
    alerts = briefing.get("alerts", [])
    system_confidence = briefing.get("system_confidence", 0.7)
    consolidated_action = briefing.get("consolidated_price_action", price_action)
    consolidation_rationale = briefing.get("consolidation_rationale", "")
    critical_issues = briefing.get("critical_issues", [])
    signal_sources = briefing.get("signal_sources", [])
    derived_overall_status = briefing.get("derived_overall_status", "")
    recommended_priority_actions_seed = briefing.get("recommended_priority_actions_seed", [])
    decision_drivers = briefing.get("decision_drivers", [])
    decision_penalties = briefing.get("decision_penalties", [])
    severity_summary = briefing.get("severity_summary", {})
    action_constraints = briefing.get("action_constraints", [])
    strategy_label = briefing.get("strategy_label", "")
    strategy_rationale = briefing.get("strategy_rationale", "")
    strategy_drivers = briefing.get("strategy_drivers", [])
    strategy_risks = briefing.get("strategy_risks", [])
    strategy_confidence = briefing.get("strategy_confidence", 0)
    strategy_influence_on_decision = briefing.get("strategy_influence_on_decision", "")
    strategy_scorecard = briefing.get("strategy_scorecard", {})
    strategy_counter_signals = briefing.get("strategy_counter_signals", [])
    strategy_confidence_reason = briefing.get("strategy_confidence_reason", "")
    alert_summary = briefing.get("alert_summary", "")
    alert_high_count = briefing.get("alert_high_count", 0)
    alert_critical_count = briefing.get("alert_critical_count", 0)
    market_signals = briefing.get("market_signals", [])
    market_signal_summary = briefing.get("market_signal_summary", "")
    market_raise_signal_count = briefing.get("market_raise_signal_count", 0)
    market_lower_signal_count = briefing.get("market_lower_signal_count", 0)
    market_caution_signal_count = briefing.get("market_caution_signal_count", 0)
    recommended_actions = briefing.get("recommended_actions", [])
    recommended_action_summary = briefing.get("recommended_action_summary", "")
    urgent_action_count = briefing.get("urgent_action_count", 0)
    high_priority_action_count = briefing.get("high_priority_action_count", 0)
    top_notifications = briefing.get("top_notifications", [])
    notification_summary = briefing.get("notification_summary", "")
    notification_priority_counts = briefing.get("notification_priority_counts", {})
    memory_summary = briefing.get("memory_summary", "")
    repeated_alerts = briefing.get("repeated_alerts", [])
    new_alerts = briefing.get("new_alerts", [])
    resolved_alerts = briefing.get("resolved_alerts", [])
    strategy_changed = briefing.get("strategy_changed", False)
    overall_status_changed = briefing.get("overall_status_changed", False)
    attention_trend = briefing.get("attention_trend", "stable")
    previous_snapshot_found = briefing.get("previous_snapshot_found", False)
    action_shift = briefing.get("action_shift")
    opportunities = briefing.get("opportunities", [])
    opportunity_summary = briefing.get("opportunity_summary", "")
    high_opportunity_count = briefing.get("high_opportunity_count", 0)
    opportunity_types = briefing.get("opportunity_types", [])
    executive_summary_seed = briefing.get("executive_summary_seed", [])
    executive_priority_order = briefing.get("executive_priority_order", [])
    executive_section_hints = briefing.get("executive_section_hints", {})
    executive_top_risks = briefing.get("executive_top_risks", [])
    executive_top_actions = briefing.get("executive_top_actions", [])
    executive_top_opportunities = briefing.get("executive_top_opportunities", [])
    executive_include_memory = briefing.get("executive_include_memory", False)
    impact_summary = briefing.get("impact_summary", "")
    top_value_opportunity = briefing.get("top_value_opportunity")
    impact_opportunities = briefing.get("impact_opportunities", [])
    impact_actions = briefing.get("impact_actions", [])
    value_opportunities = briefing.get("value_opportunities", [])
    value_actions = briefing.get("value_actions", [])
    value_summary = briefing.get("value_summary", "")
    top_priority_item = briefing.get("top_priority_item")
    scenario_assessment = briefing.get("scenario_assessment", [])
    scenario_summary = briefing.get("scenario_summary", "")
    recommended_scenario = briefing.get("recommended_scenario", "")
    scenario_risks = briefing.get("scenario_risks", [])
    scenario_tradeoffs = briefing.get("scenario_tradeoffs", [])
    change_summary = briefing.get("change_summary", "")
    change_severity = briefing.get("change_severity", "low")
    change_highlights = briefing.get("change_highlights", [])
    strategy_changed = briefing.get("strategy_changed", False)
    overall_status_changed = briefing.get("overall_status_changed", False)
    consolidated_action_changed = briefing.get("consolidated_action_changed", False)
    top_priority_changed = briefing.get("top_priority_changed", False)
    recommended_scenario_changed = briefing.get("recommended_scenario_changed", False)
    new_critical_alerts = briefing.get("new_critical_alerts", [])
    resolved_critical_alerts = briefing.get("resolved_critical_alerts", [])

    # Textos humanizados para el informe (estructura de 5 bloques)
    events_formatted = _format_events_for_report(events or [])
    pos_phrase, strat_label_inferred = _infer_price_positioning_language(outputs)
    strategy_human = _build_human_strategy_message(briefing, outputs, pos_phrase, strat_label_inferred)
    confidence_human = _build_human_confidence_message(system_confidence)
    parity_human = _build_parity_message(parity_status or "ok", channels_mentioned=False)

    # Room type recommendations (solo dicts para evitar .get sobre no-dict)
    room_recs = [r for r in (pricing.get("room_type_analysis") or []) if isinstance(r, dict)]
    room_recs_text = "\n".join([
        f"  {r.get('type','?')}: {r.get('your_price','?')}€ → "
        f"{r.get('recommended_price','?')}€ ({r.get('change_pct',0):+.1f}%) — {r.get('justification','')}"
        for r in room_recs
    ]) if room_recs else "  (sin datos por tipo de habitación)"

    conflicts_safe = [c for c in (conflicts or [])[:5] if isinstance(c, dict)]
    conflicts_text = "\n".join([
        f"  {c.get('description','?')} → {c.get('resolution_hint','?')}"
        for c in conflicts_safe
    ]) if conflicts_safe else "  Ninguno."

    seed_safe = [s for s in (recommended_priority_actions_seed or [])[:5] if isinstance(s, dict)]
    seed_actions = "\n".join(
        f"  [{s.get('urgency','?')}] {s.get('action_hint','')}" for s in seed_safe
    ) if seed_safe else "  (vacío)"

    summary_seed_lines = _normalize_list_of_strings((executive_summary_seed or [])[:4], 80)
    summary_seed_text = chr(10).join(f"  {i+1}. {s}" for i, s in enumerate(summary_seed_lines)) if summary_seed_lines else "  (vacío)"
    top_risks_safe = _normalize_list_of_dicts((executive_top_risks or [])[:3], ["type", "severity", "message"])
    top_actions_safe = _normalize_list_of_dicts((executive_top_actions or [])[:3], ["type", "title"])
    top_opps_safe = _normalize_list_of_dicts((executive_top_opportunities or [])[:3], ["type", "title"])
    decision_drivers_safe = _normalize_list_of_strings((decision_drivers or [])[:3], 200)

    return f"""Genera el informe diario para el director del hotel. La pregunta central es: ¿Mi precio actual está bien o qué debería hacer y por qué?

HOTEL: {hotel_name}
FECHA: {date}

TEXTOS PARA INCORPORAR (usa estos para redactar de forma humana; no copies literal si no encaja, pero sí el tono):
- Eventos: {events_formatted or "(ninguno detectado)"}
- Posición del hotel vs compset: {pos_phrase or "(no calculada con los datos disponibles)"}
- Interpretación estratégica (usa como base): {strategy_human or "(elabora a partir del briefing y la acción consolidada)"}
- Nota de confianza (incluir solo si no está vacío): {confidence_human or "(omitir)"}
- Paridad entre canales: {parity_human}

DATOS NUMÉRICOS:
Precio hotel {your_adr}€ | Media compset {market_avg}€ | Posición ranking {your_rank}/{total_compset} | ARI {ari} RGI {rgi}
Demanda: score {demand_score} señal {demand_signal}
Reputación: GRI {gri} | Visibilidad {visibility} | Posición Booking (usar con prudencia): {booking_pos}

DECISIÓN CONSOLIDADA: {consolidated_action.upper()}
Racional: {(consolidation_rationale or "N/A")[:150]}
Estado general: {derived_overall_status or 'stable'}
Drivers: {decision_drivers_safe}

Semilla de acciones prioritarias (máximo 3; expandir con detalle):
{seed_actions}

Estrategia: {strategy_label or 'BALANCED'} — {strategy_rationale or 'Postura neutra.'}
Escenario: {recommended_scenario or 'hold'} — {scenario_summary or 'N/A'}
Alertas: {alert_summary or 'Ninguna'}
Señales de mercado: {market_signal_summary or 'Ninguna'}
Conflictos: {conflicts_text}

ESTRUCTURA OBLIGATORIA de report_text (en este orden, párrafos separados por \\n\\n):
1. RECOMENDACIÓN — Una frase clara: subir ligeramente el precio / mantener el precio actual / revisar a la baja.
2. CONTEXTO DE MERCADO — Demanda, eventos (enumerar si hay nombres; si no, usar la frase de eventos anterior), competencia.
3. POSICIÓN DEL HOTEL — Precio vs compset (por debajo / alineado / por encima).
4. INTERPRETACIÓN ESTRATÉGICA — Qué estrategia refleja el precio y por qué tiene o no sentido ahora.
5. ACCIÓN SUGERIDA — Recomendación práctica para cerrar.

REGLAS: Tono humano, cercano, profesional. Prohibido: "Market indicates hold", "Strategy adequate", "Te equivocas". overall_status: {derived_overall_status or 'stable'}. Máximo 400 palabras en report_text. Máximo 3 priority_actions. Citar fuentes en reason.

Devuelve ÚNICAMENTE este JSON (sin texto antes ni después):

{{
  "email_subject": "asunto <60 caracteres",
  "overall_status": "strong|stable|needs_attention|alert",
  "status_summary": "una frase sobre la situación de hoy",
  "report_text": "cuerpo en texto plano. Párrafos con \\n\\n. Estructura: RECOMENDACIÓN, CONTEXTO DE MERCADO, POSICIÓN DEL HOTEL, INTERPRETACIÓN ESTRATÉGICA, ACCIÓN SUGERIDA. Máximo 400 palabras.",
  "priority_actions": [
    {{ "rank": 1, "urgency": "immediate|this_week|this_month", "action": "qué hacer", "room_type": "general", "metric": "", "reason": "fuente", "expected_impact": "" }}
  ],
  "weekly_watchlist": "una tendencia a vigilar esta semana"
}}
"""


async def build_full_report_html(
    full_analysis: dict,
    report_data: dict,
    api_key: str = "",
) -> str:
    """Construye el HTML completo del email usando los datos del informe."""
    from mailer.report_mailer_v2 import build_email_html_v2
    return build_email_html_v2(full_analysis, report_data)
