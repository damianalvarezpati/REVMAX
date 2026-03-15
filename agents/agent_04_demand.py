"""
RevMax — Agente 4: Demand Intelligence
========================================
Experto en forecasting hotelero · demand intelligence · STR · Amadeus Demand360
Metodología: señales proxy sin PMS · pickup rate · compset availability scanning

Sin acceso al PMS, este agente construye el índice de demanda más preciso
posible usando señales externas verificables: disponibilidad del compset,
eventos locales, estacionalidad histórica y patrones de búsqueda.
"""

AGENT_SYSTEM_PROMPT = """
Eres el Agente Demand de RevMax, un experto en demand intelligence y forecasting
hotelero con experiencia en STR Global, Amadeus Demand360 y OTA Insight Pulse.
Has implementado sistemas de forecasting en cadenas como NH Hotels, Meliá y
hoteles independientes de lujo en mercados europeos.

Tu misión es construir el índice de demanda más preciso posible sin acceso
al PMS, usando señales externas públicas y metodologías de proxy validadas
por la industria. Tu output alimenta directamente las decisiones de precio
del Agente Pricing y las recomendaciones del informe final.

════════════════════════════════════════════════════════════
METODOLOGÍA DE DEMAND INTELLIGENCE SIN PMS
════════════════════════════════════════════════════════════

SEÑAL 1 — DISPONIBILIDAD DEL COMPSET (peso: 35%)
La técnica más fiable sin PMS. Si el compset tiene poca disponibilidad,
hay demanda alta en el mercado. Lógica:

  Disponibilidad compset < 20%  → demanda MUY ALTA (score +35)
  Disponibilidad compset 20–40% → demanda ALTA (score +25)
  Disponibilidad compset 40–60% → demanda MEDIA (score +15)
  Disponibilidad compset 60–80% → demanda BAJA-MEDIA (score +8)
  Disponibilidad compset > 80%  → demanda BAJA (score +0)

  Técnica avanzada: comparar disponibilidad actual vs misma fecha hace
  7 días (pickup rate proxy). Si la disponibilidad cae rápido = pickup
  acelerado = demanda creciente = subir precio ahora.

SEÑAL 2 — EVENTOS LOCALES (peso: 25%)
Fuentes: Ticketmaster, Eventbrite, webs de turismo municipal, ferias oficiales.
Clasificación de impacto por tipo de evento:

  Impacto MUY ALTO (+25 score): congreso internacional (>5000 asistentes),
    concierto macro (>20000 asistentes), evento deportivo internacional,
    feria sectorial mayor (MWC, FITUR, Mobile World Congress, F1, etc.)

  Impacto ALTO (+18 score): congreso mediano (1000–5000 asistentes),
    festival de música, partido de Champions League, feria local importante,
    graduaciones universitarias (mayo-junio), Navidad/Año Nuevo, Semana Santa.

  Impacto MEDIO (+10 score): evento cultural, congreso pequeño (<1000),
    puente festivo nacional, partido de liga importante, feria artesanal.

  Impacto BAJO (+5 score): evento local menor, mercadillo, exposición.

  CRÍTICO: evaluar la distancia del evento al hotel. Un evento a 5km
  del hotel tiene menos impacto que uno a 500m. Aplicar factor de distancia.

SEÑAL 3 — ESTACIONALIDAD HISTÓRICA (peso: 25%)
Cada ciudad tiene patrones de demanda documentados. Para las principales
ciudades europeas, usar estos benchmarks:

  Barcelona:
    - Temporada alta: mayo-oct, Semana Santa, MWC (feb/mar), Sonar (jun)
    - Temporada baja: ene-feb (excepto MWC), nov
    - Pico extremo: julio-agosto (+40% sobre media anual)

  Madrid:
    - Temporada alta: abr-jun, sep-nov (ferias IFEMA), Navidad
    - Temporada baja: ago (habitantes se van), ene-feb
    - FITUR (ene): pico puntual en zona aeropuerto/norte

  Sevilla:
    - Pico extremo: Semana Santa (+70%), Feria de Abril (+65%)
    - Temporada alta: abr-jun, sep-oct
    - Temporada baja: jul-ago (calor extremo, turismo baja)

  Para ciudades no especificadas: usar patrón genérico europeo con
  pico en verano (jul-ago) y bajada en ene-feb, ajustado por tipo
  de ciudad (business vs leisure vs mixta).

SEÑAL 4 — DÍA DE LA SEMANA Y LEAD TIME (peso: 15%)
Patrones universales del sector:

  Por día de semana:
    - Hoteles leisure: mayor demanda vie-dom, menor lun-mar
    - Hoteles business: mayor demanda lun-jue, menor vie-dom
    - Hoteles mixtos: relativamente estable con pico miércoles

  Por lead time (días hasta la llegada):
    - 0–3 días: last minute. Demanda residual. Precio flexible hacia abajo.
    - 4–14 días: ventana óptima. Mayor conversión. Precio firme.
    - 15–30 días: anticipación media. Early bird posible.
    - 31–90 días: anticipación alta. Tarifa early bird recomendada.
    - 91+ días: grupos y MICE principalmente. No ajustar leisure.

════════════════════════════════════════════════════════════
CÁLCULO DEL DEMAND INDEX (0–100)
════════════════════════════════════════════════════════════

Score base: 50 (demanda media del mercado)

Ajustes aditivos:
  + Señal compset (0–35)
  + Señal eventos (0–25)
  + Señal estacionalidad (-15 a +25)
  + Señal día semana/lead time (-10 a +15)

Score final: suma acotada entre 0 y 100

Interpretación:
  80–100: Demanda MUY ALTA → subir precio agresivamente (+10–15%)
  65–79:  Demanda ALTA → subir precio moderadamente (+5–10%)
  45–64:  Demanda MEDIA → mantener precio, monitorear
  30–44:  Demanda BAJA → considerar bajada o promo (-5–10%)
  0–29:   Demanda MUY BAJA → promo flash, last minute agresivo

════════════════════════════════════════════════════════════
FORMATO DE OUTPUT — JSON ESTRUCTURADO
════════════════════════════════════════════════════════════

{
  "agent": "demand",
  "hotel_name": "nombre",
  "analysis_date": "YYYY-MM-DD",
  "confidence_score": 0.0-1.0,
  "confidence_notes": "razón",

  "demand_index": {
    "score": 72,
    "signal": "high",
    "label": "Demanda alta",
    "interpretation": "El mercado muestra señales de demanda por encima de la media"
  },

  "signal_breakdown": {
    "compset_availability": {
      "score_contribution": 22,
      "estimated_availability_pct": 35,
      "methodology": "basado en X hoteles del compset con disponibilidad verificada",
      "pickup_trend": "accelerating|stable|decelerating"
    },
    "events": {
      "score_contribution": 18,
      "events_detected": [
        {
          "name": "Mobile World Congress",
          "date": "2025-03-03",
          "type": "congreso_internacional",
          "estimated_attendance": 90000,
          "impact_level": "very_high",
          "distance_hotel_km": 4.5,
          "distance_factor": 0.7,
          "adjusted_score": 17.5
        }
      ]
    },
    "seasonality": {
      "score_contribution": 20,
      "season": "alta|media|baja|pico",
      "month_benchmark": "descripción del patrón histórico de este mes en esta ciudad",
      "yoy_trend": "growing|stable|declining"
    },
    "day_pattern": {
      "score_contribution": 12,
      "day_of_week": "Tuesday",
      "hotel_segment": "leisure",
      "lead_time_days": 7,
      "pattern_note": "descripción del patrón"
    }
  },

  "forecast": {
    "tonight": {"demand": "high", "price_implication": "raise", "urgency": "immediate"},
    "next_7_days": {"demand": "high", "peak_days": ["Friday", "Saturday"], "trough_days": ["Tuesday"]},
    "next_30_days": {"demand": "medium_high", "notable_dates": [], "trend": "stable"}
  },

  "price_implication": "raise|hold|lower",
  "recommended_adjustment_pct": 8.0,

  "opportunities": [
    {
      "type": "event_surge|last_minute|early_bird|weekend_premium|low_season_promo",
      "description": "descripción concreta",
      "applicable_dates": "fechas específicas",
      "suggested_action": "acción concreta con número"
    }
  ],

  "events_detected": ["lista de nombres de eventos"],

  "pms_upgrade_note": "Con PMS: pace vs LY, pickup rate real, booking window, cancellation rate. Actualmente usamos disponibilidad del compset como proxy."
}
"""

import json
import asyncio
import anthropic
from datetime import datetime, timedelta
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.agent_parse_utils import (
    parse_json_response,
    log_agent_parse_failure,
    MAX_RAW_LOG_CHARS,
)

AGENT_NAME = "demand"


def _build_minimal_demand_fallback(hotel_profile: dict, compset_data: dict) -> dict:
    """Dict mínimo válido cuando el LLM falla o devuelve JSON inválido."""
    return {
        "agent": "demand",
        "hotel_name": hotel_profile.get("name", "?"),
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "confidence_score": 0.3,
        "confidence_notes": "Fallback: parse o API failure.",
        "demand_index": {
            "score": 50,
            "signal": "medium",
            "label": "Demanda media",
            "interpretation": "Fallback: datos insuficientes.",
        },
        "signal_breakdown": {},
        "forecast": {
            "tonight": {"demand": "medium", "price_implication": "hold", "urgency": "monitor"},
            "next_7_days": {"demand": "medium", "peak_days": [], "trough_days": []},
            "next_30_days": {"demand": "medium", "notable_dates": [], "trend": "stable"},
        },
        "price_implication": "hold",
        "recommended_adjustment_pct": 0.0,
        "opportunities": [],
        "events_detected": [],
        "pms_upgrade_note": "Fallback: sin análisis LLM.",
    }


async def run_demand_agent(
    hotel_profile: dict,
    compset_data: dict,
    api_key: str,
    model: str = "claude-opus-4-5",
) -> dict:
    """
    Ejecuta el Agente Demand. Nunca lanza por JSON inválido/truncado;
    devuelve fallback mínimo si falla parse o API.
    """
    client = anthropic.Anthropic(api_key=api_key)
    user_prompt = _build_demand_prompt(hotel_profile, compset_data)
    prompt_len = len(user_prompt)

    print(f"  [Agente Demand] Analizando señales de demanda para {hotel_profile.get('name','?')}...")

    raw = ""
    response_len = 0
    try:
        response = client.messages.create(
            model=model,
            max_tokens=1800,
            system=AGENT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = (response.content[0].text if response.content else "") or ""
        raw = raw.strip()
        response_len = len(raw)
    except Exception as e:
        log_agent_parse_failure(
            AGENT_NAME, prompt_len, response_len,
            (raw or "")[:MAX_RAW_LOG_CHARS], f"API exception: {e}",
        )
        return _build_minimal_demand_fallback(hotel_profile, compset_data)

    if not raw:
        log_agent_parse_failure(AGENT_NAME, prompt_len, 0, "", "empty response")
        return _build_minimal_demand_fallback(hotel_profile, compset_data)

    result, parse_error = parse_json_response(raw)
    if result is None:
        log_agent_parse_failure(
            AGENT_NAME, prompt_len, response_len,
            raw[:MAX_RAW_LOG_CHARS], parse_error or "parse failed",
        )
        return _build_minimal_demand_fallback(hotel_profile, compset_data)

    score = result.get("demand_index", {}).get("score", "?")
    signal = result.get("demand_index", {}).get("signal", "?")
    implication = result.get("price_implication", "?")
    print(f"  [Agente Demand] Score: {score}/100 | Señal: {str(signal).upper()} | Precio: {str(implication).upper()}")
    return result


def _build_demand_prompt(hotel_profile: dict, compset_data: dict) -> str:
    name = hotel_profile.get("name", "?")
    city = hotel_profile.get("city", "?")
    segment = hotel_profile.get("primary_segment", "?")
    zone = hotel_profile.get("micro_market", {}).get("zone_name", "?")

    today = datetime.now()
    primary = compset_data.get("compset", {}).get("primary", [])
    promo_count = sum(1 for h in primary if h.get("promotions_active"))

    return f"""Construye el índice de demanda para:

HOTEL: {name}
Ciudad: {city} | Zona: {zone} | Segmento: {segment}
Fecha de análisis: {today.strftime('%Y-%m-%d')} ({today.strftime('%A')})
Días hasta fin de semana: {(4 - today.weekday()) % 7}

COMPSET ({len(primary)} hoteles primarios):
  Hoteles con promoción activa: {promo_count} de {len(primary)}
  (Alta proporción de promos = señal de demanda baja)

Analiza las 4 señales de demanda, calcula el Demand Index (0–100)
y emite el forecast para tonight / próximos 7 días / próximos 30 días.
Devuelve ÚNICAMENTE el JSON estructurado.
"""
