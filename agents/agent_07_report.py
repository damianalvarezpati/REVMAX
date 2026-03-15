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
import asyncio
import anthropic
from datetime import datetime
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def run_report_agent(
    full_analysis: dict,
    api_key: str,
    model: str = "claude-opus-4-5",
) -> dict:
    """
    Recibe el análisis completo del orquestador y genera el informe.
    Devuelve: { email_subject, report_text, priority_actions, html_ready }
    """
    client = anthropic.Anthropic(api_key=api_key)
    user_prompt = _build_report_prompt(full_analysis)

    hotel_name = full_analysis.get("hotel_name", "el hotel")
    print(f"  [Agente Report] Redactando informe ejecutivo para {hotel_name}...")

    response = client.messages.create(
        model=model,
        max_tokens=1200,
        system=AGENT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )

    raw = response.content[0].text.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            result = json.loads(match.group())
        else:
            # Si no devuelve JSON, estructurarlo manualmente
            result = {
                "email_subject": f"RevMax · {hotel_name} · {datetime.now().strftime('%d %b')}",
                "report_text": raw,
                "priority_actions": [],
                "overall_status": "needs_attention",
            }

    print(f"  [Agente Report] ✓ Informe generado — asunto: {result.get('email_subject','?')[:60]}")
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

    # Room type recommendations
    room_recs = pricing.get("room_type_analysis", [])
    room_recs_text = "\n".join([
        f"  {r.get('type','?')}: {r.get('your_price','?')}€ → "
        f"{r.get('recommended_price','?')}€ ({r.get('change_pct',0):+.1f}%) — {r.get('justification','')}"
        for r in room_recs
    ]) if room_recs else "  (sin datos por tipo de habitación)"

    conflicts_text = "\n".join([
        f"  CONFLICTO: {c.get('description','?')} → {c.get('resolution_hint','?')}"
        for c in conflicts
    ]) if conflicts else "  Ninguno detectado."

    return f"""Genera el informe diario ejecutivo para:

HOTEL: {hotel_name}
FECHA: {date} ({datetime.now().strftime('%A')})
CONFIDENCE DEL SISTEMA: {system_confidence}

═══ BRIEFING EJECUTIVO (estructura obligatoria del informe; derivado por código) ═══
ORDEN DE SECCIONES (respeta este orden en report_text): {executive_priority_order}
RESUMEN EJECUTIVO SEMILLA (usa estas 4 líneas como base del resumen inicial; no las copies literalmente, redáctalas en tono ejecutivo):
{chr(10).join(f'  {i+1}. {s}' for i, s in enumerate(executive_summary_seed)) if executive_summary_seed else '  (vacío)'}
TOP RIESGOS (máximo 2-3; solo estos en la sección Critical Risks): {json.dumps(executive_top_risks, ensure_ascii=False)}
TOP ACCIONES (máximo 3; solo estas en Recommended Actions): {json.dumps([{{"type": a.get("type"), "priority": a.get("priority"), "title": a.get("title")}} for a in executive_top_actions], ensure_ascii=False)}
TOP OPORTUNIDADES (máximo 2-3; solo estas en Opportunities): {json.dumps([{{"type": o.get("type"), "level": o.get("opportunity_level"), "title": o.get("title")}} for o in executive_top_opportunities], ensure_ascii=False)}
INCLUIR MEMORIA RECIENTE: {executive_include_memory} (si False, no incluyas sección Recent Memory en report_text)
PISTAS POR SECCIÓN: {json.dumps(executive_section_hints, ensure_ascii=False)}

═══ RESUMEN DE AGENTES ════════════════════════════════

PRICING:
  Tu ADR: {your_adr}€ | Media compset: {market_avg}€
  Posición: #{your_rank} de {total_compset}
  ARI: {ari} | RGI: {rgi} | Cuadrante: {quadrant}
  Acción consolidada: {consolidated_action.upper()}
  Acción primaria: {price_primary}

POR TIPO DE HABITACIÓN:
{room_recs_text}

DEMAND:
  Score: {demand_score}/100 | Señal: {demand_signal.upper()}
  Eventos: {', '.join(events) if events else 'ninguno'}
  Próximos 7 días: {forecast_7d.get('demand','?')} | Pico: {', '.join(forecast_7d.get('peak_days',[]))}

REPUTATION:
  GRI: {gri} | vs compset: {gri_vs_compset:+} pts
  Temas negativos: {', '.join(neg_themes) if neg_themes else 'ninguno relevante'}
  Percepción de precio: {price_perception}

DISTRIBUTION:
  Visibilidad: {visibility} | Posición Booking: #{booking_pos}
  Paridad: {parity_status.upper()}
  Quick wins: {quick_wins[0].get('action','ninguno') if quick_wins else 'ninguno'}

DECISIÓN CONSOLIDADA (usa esto como referencia obligatoria):
  Acción: {consolidated_action.upper()}
  Racional: {consolidation_rationale or 'No especificado.'}
  Señales: {chr(10).join(f'  - {s}' for s in signal_sources) if signal_sources else '  (no detallado)'}
  Asuntos críticos: {chr(10).join(f'  - {i}' for i in critical_issues) if critical_issues else '  Ninguno.'}

ESTADO Y PRIORIDAD DERIVADOS POR CÓDIGO (respeta estos valores; no inventes un tono distinto):
  derived_overall_status: {derived_overall_status or 'stable'}
  decision_drivers: {chr(10).join(f'  - {d}' for d in decision_drivers) if decision_drivers else '  (no detallado)'}
  decision_penalties: {chr(10).join(f'  - {p}' for p in decision_penalties) if decision_penalties else '  Ninguna.'}
  severity_summary: {json.dumps(severity_summary) if severity_summary else '{}'}
  action_constraints: {chr(10).join(f'  - {c}' for c in action_constraints) if action_constraints else '  Ninguna.'}
  recommended_priority_actions_seed (base obligatoria para priority_actions; expande con detalle, no contradigas urgencia ni orden):
{chr(10).join(f'  - [{s.get("urgency","?")}] {s.get("reason_source","?")}: {s.get("action_hint","")}' for s in recommended_priority_actions_seed) if recommended_priority_actions_seed else '  (vacío)'}

ESTRATEGIA DERIVADA (nómbrala en el informe y conecta con las acciones):
  strategy_label: {strategy_label or 'BALANCED'}
  strategy_rationale: {strategy_rationale or 'Postura neutra.'}
  strategy_drivers: {chr(10).join(f'  - {d}' for d in strategy_drivers) if strategy_drivers else '  (no detallado)'}
  strategy_risks: {chr(10).join(f'  - {r}' for r in strategy_risks) if strategy_risks else '  Ninguno.'}
  strategy_confidence: {strategy_confidence}
  strategy_confidence_reason: {strategy_confidence_reason or 'No especificado.'}
  strategy_scorecard (señales que apoyan la estrategia): {json.dumps(strategy_scorecard) if strategy_scorecard else '{}'}
  strategy_counter_signals (señales en contra; reconocer límites): {chr(10).join(f'  - {c}' for c in strategy_counter_signals) if strategy_counter_signals else '  Ninguna.'}
  strategy_influence_on_decision: {strategy_influence_on_decision or 'N/A'}

CONFLICTOS ENTRE AGENTES:
{conflicts_text}

OPORTUNIDADES IDENTIFICADAS POR REVMAX (generadas por Opportunity Engine; no inventar oportunidades fuera de esta lista):
  opportunity_summary: {opportunity_summary or 'Ninguna.'}
  high_opportunity_count: {high_opportunity_count}
  opportunity_types: {opportunity_types}
  Lista de oportunidades (estructura; para impacto usar impact_opportunities más abajo):
{chr(10).join(f'  [{o.get("opportunity_level","?").upper()}] {o.get("type","?")}: {o.get("title","?")} | summary: {o.get("summary","")}' for o in opportunities) if opportunities else '  (vacío)'}

IMPACTO POR OPORTUNIDAD (Impact Engine; usar SOLO esta lista para impact_estimate, impact_confidence, impact_reason en el informe; no inventar):
  impact_summary: {impact_summary or 'N/A'}
  top_value_opportunity: {json.dumps(top_value_opportunity, ensure_ascii=False) if top_value_opportunity else 'N/A'}
  impact_opportunities (citar solo estos impactos en el report_text):
{chr(10).join(f'  [{o.get("opportunity_level","?").upper()}] {o.get("type","?")}: {o.get("title","?")} | summary: {o.get("summary","")} | impact_estimate: {o.get("impact_estimate","impact uncertain")} | impact_confidence: {o.get("impact_confidence","low")} | impact_reason: {o.get("impact_reason","")}' for o in impact_opportunities) if impact_opportunities else '  (vacío)'}

ALERTAS DETECTADAS POR REVMAX (generadas por código; si hay high o critical deben aparecer en el informe):
  alert_summary: {alert_summary or 'Ninguna.'}
  alert_high_count: {alert_high_count}
  alert_critical_count: {alert_critical_count}
  Lista de alertas:
{chr(10).join(f'  [{a.get("severity","?").upper()}] {a.get("type","?")} ({a.get("source","?")}): {a.get("message","?")}' for a in alerts) if alerts else '  Ninguna.'}

SEÑALES DE MERCADO DETECTADAS POR REVMAX (usan para reforzar el "por qué"; no inventar señales fuera de esta lista):
  market_signal_summary: {market_signal_summary or 'Ninguna.'}
  market_raise_signal_count: {market_raise_signal_count}
  market_lower_signal_count: {market_lower_signal_count}
  market_caution_signal_count: {market_caution_signal_count}
  Lista de señales:
{chr(10).join(f'  [{s.get("strength","?")}] {s.get("type","?")} → {s.get("directional_effect","?")} ({s.get("source","?")}): {s.get("message","?")}' for s in market_signals) if market_signals else '  Ninguna.'}

ACCIONES RECOMENDADAS POR REVMAX (generadas por Decision Engine; las priority_actions deben basarse SOLO en esta lista; no inventar ninguna acción fuera de ella):
  recommended_action_summary: {recommended_action_summary or 'Ninguna.'}
  urgent_action_count: {urgent_action_count}
  high_priority_action_count: {high_priority_action_count}
  Lista de acciones (estructura; para impacto usar impact_actions más abajo):
{chr(10).join(f'  [{a.get("priority","?").upper()}] {a.get("type","?")} ({a.get("horizon","?")}): {a.get("title","?")} | rationale: {a.get("rationale","")}' for a in recommended_actions) if recommended_actions else '  (vacío)'}

IMPACTO POR ACCIÓN (Impact Engine; usar SOLO esta lista para action_impact_estimate, action_impact_confidence en el informe; no inventar):
  impact_actions (citar solo estos impactos en el report_text):
{chr(10).join(f'  [{a.get("priority","?").upper()}] {a.get("type","?")}: {a.get("title","?")} | action_impact_estimate: {a.get("action_impact_estimate","impact uncertain")} | action_impact_confidence: {a.get("action_impact_confidence","low")}' for a in impact_actions) if impact_actions else '  (vacío)'}

PRIORIZACIÓN POR VALOR Y URGENCIA (Value Prioritization Engine; usar SOLO estos datos para priority ranking, value_score y urgency en el informe; no inventar scores; mostrar máximo 3 prioridades):
  value_summary: {value_summary or 'N/A'}
  top_priority_item: {json.dumps(top_priority_item, ensure_ascii=False) if top_priority_item else 'N/A'}
  value_opportunities (ordenadas por priority_score DESC; citar priority_rank, value_score, urgency_score, priority_score, impact_estimate):
{chr(10).join(f'  #{o.get("priority_rank", "?")} [{o.get("type","?")}] {o.get("title","?")} | value_score: {o.get("value_score", 0)} | urgency_score: {o.get("urgency_score", 0)} | priority_score: {o.get("priority_score", 0)} | impact_estimate: {o.get("impact_estimate","")}' for o in value_opportunities[:5]) if value_opportunities else '  (vacío)'}
  value_actions (ordenadas por priority_score DESC; citar priority_rank, value_score, urgency_score, priority_score, action_impact_estimate):
{chr(10).join(f'  #{a.get("priority_rank", "?")} [{a.get("type","?")}] {a.get("title","?")} | value_score: {a.get("value_score", 0)} | urgency_score: {a.get("urgency_score", 0)} | priority_score: {a.get("priority_score", 0)} | action_impact_estimate: {a.get("action_impact_estimate","")}' for a in value_actions[:5]) if value_actions else '  (vacío)'}

ESCENARIOS EVALUADOS POR REVMAX (Scenario Engine; solo tres escenarios: raise, hold, lower; usar en parte ejecutiva recommended_scenario y scenario_summary; no inventar escenarios fuera de estos):
  recommended_scenario: {recommended_scenario or 'hold'}
  scenario_summary: {scenario_summary or 'N/A'}
  scenario_assessment (support_score, risk_score, net_score, verdict, reason por escenario):
{chr(10).join(f'  {a.get("scenario", "?").upper()}: support={a.get("support_score", 0)} risk={a.get("risk_score", 0)} net={a.get("net_score", 0)} verdict={a.get("verdict", "?")} — {a.get("reason", "")}' for a in scenario_assessment) if scenario_assessment else '  (vacío)'}
  scenario_risks: {chr(10).join(f'  - {r}' for r in scenario_risks) if scenario_risks else '  Ninguno.'}
  scenario_tradeoffs: {chr(10).join(f'  - {t}' for t in scenario_tradeoffs) if scenario_tradeoffs else '  Ninguno.'}

NOTIFICACIONES PRIORIZADAS POR REVMAX (generadas por código; no inventar notificaciones fuera de esta lista; usar title, summary y rationale):
  notification_summary: {notification_summary or 'Ninguna.'}
  notification_priority_counts: {notification_priority_counts}
  Lista de notificaciones (top_notifications; si hay urgent/high deben influir en el tono ejecutivo del informe):
{chr(10).join(f'  [{n.get("priority","?").upper()}] {n.get("type","?")} ({n.get("delivery_intent","?")}): {n.get("title","?")} | summary: {n.get("summary","")} | rationale: {n.get("rationale","")} | source_items: {", ".join(n.get("source_items",[]))}' for n in top_notifications) if top_notifications else '  (vacío)'}

MEMORIA RECIENTE DE REVMAX (comparación con la corrida anterior; no inventar memoria fuera de la generada por código):
  previous_snapshot_found: {previous_snapshot_found}
  memory_summary: {memory_summary or 'N/A'}
  repeated_alerts: {repeated_alerts}
  new_alerts: {new_alerts}
  resolved_alerts: {resolved_alerts}
  strategy_changed: {strategy_changed}
  overall_status_changed: {overall_status_changed}
  attention_trend: {attention_trend}
  action_shift: {action_shift or 'N/A'}

═══ INSTRUCCIONES PARA EL INFORME ════════════════════

REGLAS OBLIGATORIAS:
- ESTRUCTURA EJECUTIVA: El report_text DEBE seguir el orden de executive_priority_order: 1) Executive Summary (abrir con resumen basado en executive_summary_seed: qué pasa, qué necesita atención, oportunidad principal, postura recomendada). 2) Current Strategic Posture (estrategia en una frase). 3) Critical Risks & Alerts (solo executive_top_risks; máximo 2-3). 4) Recommended Actions (solo executive_top_actions; máximo 3). 5) Opportunities (solo executive_top_opportunities; máximo 2-3). 6) Market Context (demanda y señales; breve). 7) Recent Memory (solo si executive_include_memory es True; una frase; omitir si False). No mezcles secciones ni repitas el mismo mensaje en varias. Tono ejecutivo: claro, profesional, orientado a decisión. Máximo 400 palabras. Sin jerga técnica interna ni redundancia.
- overall_status: USA el valor derived_overall_status ({derived_overall_status or 'stable'}) como overall_status del informe. No inventes "strong" si el código marcó "alert" ni "alert" si el código marcó "stable". Solo matiza si hay un dato muy claro que lo justifique.
- ACCIONES RECOMENDADAS: Las priority_actions deben BASARSE EXCLUSIVAMENTE en la lista "ACCIONES RECOMENDADAS POR REVMAX" anterior (recommended_actions). No inventes ninguna acción que no esté en esa lista. Orden: primero las urgent, luego high, luego el resto. Mantén priority, horizon y rationale de cada acción; conéctalas con strategy, alerts y market_signals en el texto. Máximo 3 priority_actions en el JSON (usa las 3 primeras de la lista o todas si son menos).
- Coherencia con consolidated_price_action y consolidation_rationale. Respetar action_constraints en el texto (ej. no recomendar subir precio si la restricción dice "Resolver paridad primero").
- Cada "reason" de las priority_actions debe CITAR LA FUENTE: ej. "Pricing: ARI bajo", "Demanda alta (score 72)", "Paridad: resolver antes de cambiar precios". Nada genérico como "mejorar revenue".
- Máximo 3 priority_actions. Orden = semilla: paridad/conflitos primero si existen, luego acción de precio consolidada.
- report_text debe explicar el "por qué" con decision_drivers y decision_penalties cuando sea relevante; usar consolidation_rationale o signal_sources para la acción de precio.
- ESTRATEGIA: Nombrar la estrategia (strategy_label: {strategy_label or 'BALANCED'}), explicar por qué RevMax interpreta esa postura (strategy_rationale, strategy_drivers) y conectar con las priority_actions. Usar strategy_confidence_reason para matizar el nivel de convicción. Si hay strategy_counter_signals, reconocerlos en 1 frase (ej. "Aunque la demanda no es especialmente alta, la reputación y el pricing sostienen una postura premium") para que el informe no suene excesivamente categórico. El scorecard sirve para trazabilidad; no hace falta citarlo literalmente en el texto.
- ALERTAS: Si hay alertas de severidad high o critical (alert_high_count: {alert_high_count}, alert_critical_count: {alert_critical_count}), debes mencionarlas en report_text en una frase clara (ej. "RevMax detecta X alerta(s) crítica(s): paridad de tarifas; resolver antes de cambiar precios"). Las priority_actions deben priorizar las alertas críticas (ej. si hay PARITY_VIOLATION, la primera acción debe ser resolver paridad). Si alert_critical_count > 0, overall_status debe ser al menos "needs_attention" o "alert"; no uses "stable" o "strong" si hay alertas críticas.
- SEÑALES DE MERCADO: Usa las market_signals para reforzar el "por qué" de la decisión consolidada. Si hay señales raise fuertes (market_raise_signal_count: {market_raise_signal_count}), conéctalas con la estrategia y las acciones en report_text. Si hay señales caution o lower (market_caution_signal_count: {market_caution_signal_count}, market_lower_signal_count: {market_lower_signal_count}), refleja prudencia en el tono. No inventes señales que no estén en la lista detectada por código.
- NOTIFICACIONES: Si hay top_notifications con prioridad urgent o high, deben influir en el tono ejecutivo del report (énfasis en lo que requiere atención inmediata o inclusión clara en el informe). No inventes notificaciones fuera de las generadas por código. Usa title, summary y rationale de cada notificación; conecta con actions y alerts en el texto.
- MEMORIA: Si hay repeated_alerts, menciónalo como persistencia del problema. Si hay resolved_alerts, menciónalo como mejora. Si strategy_changed, explícalo en una frase. Si attention_trend es worsening, el tono debe reflejar empeoramiento; si improving, reflejar mejora. No inventes memoria fuera de la generada por código (memory_summary, repeated_alerts, new_alerts, resolved_alerts, strategy_changed, attention_trend).
- OPORTUNIDADES: Si hay oportunidades de nivel high (high_opportunity_count: {high_opportunity_count}), deben aparecer en report_text. Conecta oportunidades con acciones y estrategia. No inventes oportunidades fuera de las generadas por código. Diferencia claramente oportunidad (posibilidad de captura o mejora) de alerta (riesgo) o de acción (qué hacer).
- IMPACTO: Usa SOLO impact_opportunities e impact_actions (listas anteriores) para mostrar impacto. No inventes cifras ni rangos. Si no hay estimación clara para una oportunidad o acción, indica "Estimated impact: impact uncertain." Ejemplo: "Opportunity to capture additional ADR. Estimated impact: ADR upside potential +5–9%. Confidence: medium." Mantén tono ejecutivo y no repitas el mismo texto entre secciones.
- PRIORIDAD: Usa SOLO value_opportunities y value_actions para Priority ranking, Value score y Urgency. No inventes scores. Muestra máximo 3 prioridades en el informe. Ejemplo: "Top priority opportunity: Capture additional ADR. Priority score: 8.2. Estimated impact: ADR upside +5–9%."
- ESCENARIOS: Usa SOLO los tres escenarios evaluados por código (raise, hold, lower). El informe debe poder explicar por qué el escenario recomendado (recommended_scenario) parece más defendible. Usa scenario_summary en la parte ejecutiva. No inventes escenarios fuera de los tres. Cita support_score o risk_score solo si ayuda al mensaje, sin convertir el informe en técnico.

Genera el informe siguiendo EXACTAMENTE esta estructura JSON:

{{
  "email_subject": "asunto del email <60 chars con los datos más urgentes",
  "overall_status": "strong|stable|needs_attention|alert",
  "status_summary": "1 frase que resume la situación de hoy (debe reflejar la decisión consolidada)",

  "report_text": "cuerpo del informe en texto plano, párrafos separados por \\n\\n. ESTRUCTURA OBLIGATORIA (en este orden): 1) RESUMEN EJECUTIVO (4 líneas basadas en executive_summary_seed). 2) POSTURA ESTRATÉGICA (estrategy_label en una frase). 3) RIESGOS Y ALERTAS CRÍTICAS (solo executive_top_risks). 4) ACCIONES RECOMENDADAS (solo executive_top_actions). 5) OPORTUNIDADES (solo executive_top_opportunities). 6) CONTEXTO DE MERCADO (breve). 7) MEMORIA RECIENTE (solo si executive_include_memory=True). Máximo 400 palabras. Tono ejecutivo, sin repetir el mismo mensaje en varias secciones.",

  "priority_actions": [
    {{
      "rank": 1,
      "urgency": "immediate|this_week|this_month",
      "action": "descripción exacta y ejecutable de qué hacer (qué, cuánto, en qué habitación/canal)",
      "room_type": "tipo de habitación o 'todos' o 'general'",
      "metric": "número concreto (precio en €, %, posición)",
      "reason": "razón en 1 frase CITANDO FUENTE (ej. Pricing: ARI 0.92 | Demanda: score 68)",
      "expected_impact": "impacto estimado en €, % o reservas"
    }}
  ],

  "weekly_watchlist": "1 tendencia o amenaza a vigilar esta semana en 1 frase"
}}

Devuelve ÚNICAMENTE el JSON. Sin texto adicional.
"""


async def build_full_report_html(
    full_analysis: dict,
    report_data: dict,
    api_key: str = "",
) -> str:
    """Construye el HTML completo del email usando los datos del informe."""
    from mailer.report_mailer_v2 import build_email_html_v2
    return build_email_html_v2(full_analysis, report_data)
