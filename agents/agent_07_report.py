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

    # Conflictos detectados
    conflicts = briefing.get("conflicts", [])
    opportunities = briefing.get("opportunities", [])
    alerts = briefing.get("alerts", [])
    system_confidence = briefing.get("system_confidence", 0.7)
    consolidated_action = briefing.get("consolidated_price_action", price_action)

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

CONFLICTOS ENTRE AGENTES:
{conflicts_text}

OPORTUNIDADES DETECTADAS:
{chr(10).join(f'  - {o}' for o in opportunities) if opportunities else '  Ninguna adicional.'}

ALERTAS:
{chr(10).join(f'  [{a.get("level","?").upper()}] {a.get("message","?")}' for a in alerts) if alerts else '  Ninguna.'}

═══ INSTRUCCIONES PARA EL INFORME ════════════════════

Genera el informe siguiendo EXACTAMENTE esta estructura JSON:

{{
  "email_subject": "asunto del email <60 chars con los datos más urgentes",
  "overall_status": "strong|stable|needs_attention|alert",
  "status_summary": "1 frase que resume la situación de hoy",

  "report_text": "el cuerpo completo del informe en texto plano con párrafos separados por \\n\\n, siguiendo la estructura: ESTADO HOY → POSICIÓN VS COMPETENCIA → DEMANDA → REPUTACIÓN Y VISIBILIDAD → LAS 3 ACCIONES DE HOY → ALERTA DE LA SEMANA. Máximo 400 palabras. Directo, con números.",

  "priority_actions": [
    {{
      "rank": 1,
      "urgency": "immediate|this_week|this_month",
      "action": "descripción exacta de qué hacer",
      "room_type": "tipo de habitación o 'todos' o 'general'",
      "metric": "número concreto (precio, %, posición)",
      "reason": "razón en 1 frase",
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
