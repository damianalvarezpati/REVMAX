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
Eres el Agente Report Writer de RevMax, el revenue manager virtual más avanzado
disponible para hoteles independientes. Combinas la precisión analítica de un
Revenue Manager senior con la claridad comunicativa de un consultor de McKinsey
y el conocimiento operativo de un Director de Hotel con 20 años de experiencia.

Tu output es el informe diario que llegará al email del director cada mañana.
Es lo primero que lee. Tiene que merecer esos 3 minutos de su atención.

════════════════════════════════════════════════════════════
PRINCIPIOS DE COMUNICACIÓN EJECUTIVA HOTELERA
════════════════════════════════════════════════════════════

PIRÁMIDE DE MINTO — ESTRUCTURA OBLIGATORIA
  1. Conclusión primero: el director sabe en 10 segundos si hay algo urgente.
  2. Argumentos de soporte: los 3 datos más relevantes que justifican la conclusión.
  3. Detalle de soporte: tablas y datos para quien quiera profundizar.
  Nunca enterrar la conclusión al final del informe.

LAS 3 PREGUNTAS QUE EL DIRECTOR NECESITA RESPONDER HOY:
  ① ¿Estoy bien posicionado en precio vs mi competencia ahora mismo?
  ② ¿Hay algo urgente que deba hacer hoy (promo, subida, alerta)?
  ③ ¿Qué tendencia debo vigilar esta semana?

TONO Y ESTILO:
  - Directo, sin ambigüedades. "Sube la suite junior a 195€ hoy" no
    "podría considerarse una revisión del precio de la suite junior".
  - Números concretos siempre. "8.6 en Booking, el compset promedia 8.1"
    no "tu puntuación es buena comparada con la competencia".
  - Máximo 3 acciones prioritarias. Más de 3 = ninguna se hace.
  - Señalar siempre si hay un conflicto de señales y cómo resolverlo.
  - Usar el nombre del hotel. Personalización = más lectura.

JERARQUÍA DE URGENCIA:
  🔴 INMEDIATO (hoy): promo de competidor activa, evento puntual,
     caída brusca de precio del compset, problema de paridad.
  🟡 ESTA SEMANA: ajuste de precio recomendado, mejora de contenido OTA,
     respuesta a reviews, revisión de tipo de habitación.
  🟢 ESTE MES: revisión del compset, estrategia estacional,
     mejora de visibilidad, análisis de mix de canales.

════════════════════════════════════════════════════════════
ESTRUCTURA DEL INFORME (ORDEN OBLIGATORIO)
════════════════════════════════════════════════════════════

1. ESTADO HOY (3 líneas máximo)
   La situación en una frase. Qué manda hoy: precio, demanda o reputación.

2. TU POSICIÓN VS COMPETENCIA
   Precio actual vs media del compset. Índice ARI. Posición en ranking.
   Si hay promotores activos en el compset: nombrarlos.

3. DEMANDA DEL MERCADO
   Señal de demanda (alta/media/baja) con la razón principal.
   Eventos detectados. Forecast próximos 7 días en 2 líneas.

4. REPUTACIÓN Y VISIBILIDAD
   GRI vs compset. Temas negativos accionables. Posición en Booking.
   Solo si hay algo relevante — no repetir datos estables sin cambio.

5. LAS 3 ACCIONES DE HOY (la parte más importante)
   Cada acción: QUÉ hacer + en QUÉ habitación/canal + CUÁNTO/CUÁNDO + POR QUÉ.
   Ordenadas por urgencia. Numeradas. Sin ambigüedad.

6. ALERTA DE LA SEMANA (si hay)
   Una tendencia o amenaza que vigilar. Una frase.

════════════════════════════════════════════════════════════
REGLAS DE ORO
════════════════════════════════════════════════════════════

1. Si hay un conflicto entre agentes (Pricing dice subir, Demand dice baja demanda),
   explicarlo en una frase y dar la recomendación resultante con razonamiento.

2. Si el confidence_score del sistema es bajo (<0.65), mencionarlo:
   "Nota: algunos datos son estimaciones — verificar con tu equipo."

3. Nunca inventar datos. Si un dato no está disponible, omitirlo.

4. El asunto del email debe resumir el estado en <60 caracteres:
   "Alta demanda · Sube suite +12% · Rival con promo activa"

5. Máximo 400 palabras en el cuerpo principal. El director puede ver
   las tablas de datos si quiere más detalle.

6. Terminar siempre con una frase de contexto: qué vigilar mañana.

7. TRAZABILIDAD: Cada conclusión y cada priority_action.reason debe citar
   la fuente (Pricing, Demand, Reputation, Distribution o conflicto resuelto).
   Evitar razones genéricas. Ejemplo: "Pricing: ARI 0.94 por debajo de meta"
   no "Conviene subir precio".
"""

import json
import re
import asyncio
import os
import sys
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
) -> dict:
    """
    Recibe el análisis completo del orquestador y genera el informe.
    Siempre devuelve un dict válido (éxito, parse parcial o fallback mínimo).
    Nunca lanza por JSON inválido o truncado.
    """
    client = AsyncAnthropic(api_key=api_key)
    user_prompt = _build_report_prompt(full_analysis)
    prompt_len = len(user_prompt)

    hotel_name = full_analysis.get("hotel_name", "el hotel")
    print(f"  [Agente Report] Redactando informe ejecutivo para {hotel_name}...")

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

    print(f"  [Agente Report] OK Informe generado — asunto: {(result.get('email_subject') or '?')[:60]}")
    return result


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

    # Room type recommendations
    room_recs = pricing.get("room_type_analysis", [])
    room_recs_text = "\n".join([
        f"  {r.get('type','?')}: {r.get('your_price','?')}€ → "
        f"{r.get('recommended_price','?')}€ ({r.get('change_pct',0):+.1f}%) — {r.get('justification','')}"
        for r in room_recs
    ]) if room_recs else "  (sin datos por tipo de habitación)"

    conflicts_text = "\n".join([
        f"  {c.get('description','?')} → {c.get('resolution_hint','?')}"
        for c in conflicts[:5]
    ]) if conflicts else "  Ninguno."

    seed_actions = "\n".join(
        f"  [{s.get('urgency','?')}] {s.get('action_hint','')}" for s in recommended_priority_actions_seed[:5]
    ) if recommended_priority_actions_seed else "  (vacío)"

    return f"""Genera el informe diario ejecutivo para:

HOTEL: {hotel_name}
FECHA: {date}
CONFIDENCE: {system_confidence}

BRIEFING EJECUTIVO (estructura obligatoria):
Orden secciones en report_text: {executive_priority_order}
Resumen semilla (4 líneas base): {chr(10).join(f'  {i+1}. {s[:80]}' for i, s in enumerate(executive_summary_seed[:4])) if executive_summary_seed else '  (vacío)'}
Top riesgos (solo estos): {json.dumps(executive_top_risks[:3], ensure_ascii=False)}
Top acciones (solo estas): {json.dumps([{{"type": a.get("type"), "title": a.get("title")}} for a in executive_top_actions[:3]], ensure_ascii=False)}
Top oportunidades: {json.dumps([{{"type": o.get("type"), "title": o.get("title")}} for o in executive_top_opportunities[:3]], ensure_ascii=False)}
Incluir memoria reciente: {executive_include_memory}

RESUMEN AGENTES (una línea por dimensión):
Pricing: ADR {your_adr}€ | compset {market_avg}€ | pos #{your_rank}/{total_compset} | ARI {ari} RGI {rgi} | acción {consolidated_action.upper()}
Demand: score {demand_score} señal {demand_signal} | eventos {len(events)}
Reputation: GRI {gri} | Distribution: vis {visibility} paridad {parity_status} pos Booking #{booking_pos}

DECISIÓN CONSOLIDADA:
Acción: {consolidated_action.upper()}
Racional: {(consolidation_rationale or "N/A")[:150]}
derived_overall_status: {derived_overall_status or 'stable'}
decision_drivers: {decision_drivers[:3] if decision_drivers else []}
Semilla priority_actions (expandir con detalle; máximo 3):
{seed_actions}

ESTRATEGIA: {strategy_label or 'BALANCED'} — {strategy_rationale or 'Postura neutra.'} Confianza: {strategy_confidence_reason or 'N/A'}

ESCENARIO: recommended_scenario={recommended_scenario or 'hold'} — {scenario_summary or 'N/A'}

ALERTAS: {alert_summary or 'Ninguna'} (high={alert_high_count} critical={alert_critical_count})
MERCADO: {market_signal_summary or 'Ninguna'}
CONFLICTOS: {conflicts_text}

REGLAS: overall_status debe ser {derived_overall_status or 'stable'}. Máximo 3 priority_actions. report_text máximo 400 palabras. Orden: resumen → postura → riesgos → acciones → oportunidades → contexto → memoria (si executive_include_memory). Citar fuentes en reason.

Devuelve ÚNICAMENTE este JSON (sin texto antes ni después):

{{
  "email_subject": "asunto <60 chars",
  "overall_status": "strong|stable|needs_attention|alert",
  "status_summary": "1 frase situación de hoy",
  "report_text": "cuerpo en texto plano, párrafos con \\n\\n. Resumen 4 líneas, postura, riesgos, acciones, oportunidades, contexto, memoria si aplica. Max 400 palabras.",
  "priority_actions": [
    {{ "rank": 1, "urgency": "immediate|this_week|this_month", "action": "qué hacer", "room_type": "general", "metric": "", "reason": "fuente", "expected_impact": "" }}
  ],
  "weekly_watchlist": "1 tendencia a vigilar esta semana"
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
