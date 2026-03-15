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
    opportunities = briefing.get("opportunities", [])
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

OPORTUNIDADES DETECTADAS:
{chr(10).join(f'  - {o}' for o in opportunities) if opportunities else '  Ninguna adicional.'}

ALERTAS:
{chr(10).join(f'  [{a.get("level","?").upper()}] {a.get("message","?")}' for a in alerts) if alerts else '  Ninguna.'}

═══ INSTRUCCIONES PARA EL INFORME ════════════════════

REGLAS OBLIGATORIAS:
- overall_status: USA el valor derived_overall_status ({derived_overall_status or 'stable'}) como overall_status del informe. No inventes "strong" si el código marcó "alert" ni "alert" si el código marcó "stable". Solo matiza si hay un dato muy claro que lo justifique.
- Las priority_actions deben BASARSE en recommended_priority_actions_seed: mismo orden de urgencia (immediate → this_week → this_month) y mismas fuentes (paridad, conflicto, consolidación). Expande cada ítem con action/room_type/metric/reason/expected_impact concretos, pero no contradigas la urgencia ni el mensaje de la semilla.
- Coherencia con consolidated_price_action y consolidation_rationale. Respetar action_constraints en el texto (ej. no recomendar subir precio si la restricción dice "Resolver paridad primero").
- Cada "reason" de las priority_actions debe CITAR LA FUENTE: ej. "Pricing: ARI bajo", "Demanda alta (score 72)", "Paridad: resolver antes de cambiar precios". Nada genérico como "mejorar revenue".
- Máximo 3 priority_actions. Orden = semilla: paridad/conflitos primero si existen, luego acción de precio consolidada.
- report_text debe explicar el "por qué" con decision_drivers y decision_penalties cuando sea relevante; usar consolidation_rationale o signal_sources para la acción de precio.
- ESTRATEGIA: Nombrar la estrategia (strategy_label: {strategy_label or 'BALANCED'}), explicar por qué RevMax interpreta esa postura (strategy_rationale, strategy_drivers) y conectar con las priority_actions. Usar strategy_confidence_reason para matizar el nivel de convicción. Si hay strategy_counter_signals, reconocerlos en 1 frase (ej. "Aunque la demanda no es especialmente alta, la reputación y el pricing sostienen una postura premium") para que el informe no suene excesivamente categórico. El scorecard sirve para trazabilidad; no hace falta citarlo literalmente en el texto.

Genera el informe siguiendo EXACTAMENTE esta estructura JSON:

{{
  "email_subject": "asunto del email <60 chars con los datos más urgentes",
  "overall_status": "strong|stable|needs_attention|alert",
  "status_summary": "1 frase que resume la situación de hoy (debe reflejar la decisión consolidada)",

  "report_text": "el cuerpo completo del informe en texto plano con párrafos separados por \\n\\n. Estructura: ESTADO HOY (con por qué) → POSICIÓN VS COMPETENCIA → DEMANDA → REPUTACIÓN Y VISIBILIDAD → LAS 3 ACCIONES DE HOY (con razón trazable) → ALERTA DE LA SEMANA. Máximo 400 palabras. Directo, con números. Cada conclusión debe tener causa visible.",

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
