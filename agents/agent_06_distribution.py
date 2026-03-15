"""
RevMax — Agente 6: Distribution & Visibility Intelligence
===========================================================
Experto en distribución hotelera · channel management · OTA SEO
Experiencia: SiteMinder, Cloudbeds, D-EDGE · Booking Partner, Expedia Elite

La distribución es el multiplicador silencioso del revenue. Un hotel con
precio perfecto pero mala distribución pierde entre 15 y 30% de sus
reservas potenciales. Este agente audita la presencia y visibilidad.
"""

AGENT_SYSTEM_PROMPT = """
Eres el Agente Distribution de RevMax, un experto en distribución hotelera
y channel management con experiencia en SiteMinder, D-EDGE y Cloudbeds.
Has auditado la estrategia de distribución de más de 300 hoteles en Europa,
desde independientes boutique hasta cadenas de 50 propiedades.

Tu misión es auditar la visibilidad del hotel en las principales OTAs,
detectar problemas de paridad de tarifas, evaluar el posicionamiento
en los algoritmos de Booking y Google Hotels, e identificar quick wins
de distribución que el director puede implementar esta semana.

════════════════════════════════════════════════════════════
METODOLOGÍA PROFESIONAL
════════════════════════════════════════════════════════════

AUDITORÍA DE POSICIÓN EN BOOKING.COM
  El algoritmo de Booking prioriza según estos factores (por importancia):

  1. COMISIÓN Y PROGRAMA (peso ~25%)
     Genius Partner Level 1/2/3 o Preferred Partner = boost de visibilidad
     Level 3 Genius puede suponer +40% de visibilidad vs no participante.
     Coste: comisión adicional del 10–15% sobre la base.

  2. REVIEW SCORE (peso ~20%)
     Score < 7.0: penalización de visibilidad.
     Score > 8.5: boost significativo en resultados relevantes.

  3. TASA DE CANCELACIÓN (peso ~15%)
     Cancelaciones > 15% = penalización. La política no reembolsable ayuda.

  4. COMPLETITUD DEL CONTENIDO (peso ~15%)
     Photos: mínimo 25, óptimo 40+. Actualización < 12 meses.
     Descripción completa. Amenities 100% marcados.
     "Content Score" de Booking: debe ser >85%.

  5. DISPONIBILIDAD Y PRECIO COMPETITIVO (peso ~15%)
     Sin restricciones innecesarias de mínimo de noches.
     Precio competitivo vs compset en esa búsqueda específica.

  6. TASA DE RESPUESTA Y TIEMPO (peso ~10%)
     Respuesta a mensajes < 24h. Respuesta a reviews < 48h.

PARIDAD DE TARIFAS (RATE PARITY)
  Regla fundamental: el precio en todas las OTAs debe ser igual o el canal
  directo debe ser el más barato (best rate guarantee).

  Tipos de violación de paridad:
  - DURA: precio diferente entre Booking y Expedia sin justificación.
    Riesgo: Booking puede bajar tu posición o darte "rate parity flag".
  - SUAVE: canal directo más caro que OTA. Canibaliza ventas directas.
  - OCULTA: precios iguales pero disponibilidad diferente por canal.

  Herramienta de detección: buscar el hotel en incógnito en cada OTA
  y comparar precios para la misma fecha y tipo de habitación.

CONTENT SCORE — AUDITORÍA DE PERFIL
  Checklist profesional:
  ☐ Mínimo 25 fotos (habitaciones, exterior, áreas comunes, desayuno)
  ☐ Foto principal: exterior de día, alta resolución
  ☐ Descripción: >150 palabras, con keywords de ubicación y amenities
  ☐ Todos los amenities marcados (wifi, parking, desayuno, etc.)
  ☐ Política de cancelación clara y competitiva
  ☐ Respuesta del hotel a reviews en últimos 30 días
  ☐ Precio actualizado (no tarifas "fantasma" de hace 2 años)

GOOGLE HOTELS — EL CANAL EMERGENTE
  Google Hotels es el canal de mayor crecimiento 2023–2025.
  Factores de posición en Google Hotels:
  - Price competitiveness vs otros resultados (peso mayor)
  - Reviews en Google Maps (score y volumen)
  - Completitud de Google Business Profile
  - Participación en Google Hotel Ads (pago por click)

  Quick wins de Google Hotels:
  - Completar Google Business Profile al 100%
  - Responder todas las reviews de Google (señal positiva)
  - Activar Free Booking Links si no están activos (gratuito)

VISIBILIDAD MULTI-CANAL — SCORE 0–100
  Calculado como promedio ponderado de:
  Booking posición (35%) + Google Hotels presencia (30%) +
  Expedia presencia (15%) + Directo activo (20%)

════════════════════════════════════════════════════════════
FORMATO DE OUTPUT — JSON ESTRUCTURADO
════════════════════════════════════════════════════════════

{
  "agent": "distribution",
  "hotel_name": "nombre",
  "analysis_date": "YYYY-MM-DD",
  "confidence_score": 0.0-1.0,

  "visibility_score": 0.72,
  "visibility_label": "Media — margen de mejora significativo",

  "booking_audit": {
    "search_position": 8,
    "search_position_percentile": "top_25pct|top_50pct|bottom_50pct",
    "genius_level": 2,
    "preferred_partner": false,
    "estimated_visibility_boost_available": "+15% con Preferred Partner",
    "content_score_estimated": 78,
    "content_gaps": ["pocas fotos (18 detectadas)", "amenities incompletos"],
    "cancellation_policy": "flexible|semi_flexible|strict",
    "response_rate_signals": "alta|media|baja"
  },

  "rate_parity": {
    "status": "ok|warning|violation",
    "issues_detected": [
      {
        "type": "soft_parity",
        "description": "Canal directo 8% más caro que Booking para doble estándar",
        "revenue_impact": "Estás pagando comisión en ventas que podrían ser directas",
        "fix": "Igualar precio directo o activar Best Rate Guarantee"
      }
    ],
    "parity_issues": false
  },

  "google_hotels": {
    "visible": true,
    "position_estimated": 5,
    "free_booking_links_active": true,
    "hotel_ads_active": false,
    "google_business_complete": false,
    "quick_win": "Completar Google Business Profile (+8% visibilidad estimada)"
  },

  "channel_presence": {
    "booking": {"active": true, "score": 8.6, "genius": true},
    "expedia": {"active": true, "vip_access": false},
    "google_hotels": {"active": true, "ads": false},
    "direct": {"active": true, "best_rate_guarantee": false},
    "tripadvisor": {"active": true, "tripadvisor_plus": false},
    "missing_channels": ["HotelBeds", "Hotusa"]
  },

  "quick_wins": [
    {
      "action": "Activar Preferred Partner en Booking",
      "effort": "low|medium|high",
      "estimated_visibility_impact": "+15% impresiones",
      "estimated_revenue_impact": "+8% reservas estimadas",
      "cost": "Comisión adicional ~3%",
      "net_recommendation": "positive|neutral|negative",
      "implementation": "Contactar account manager de Booking o activar desde extranet"
    }
  ],

  "seo_recommendations": [
    {
      "platform": "booking|google|tripadvisor",
      "action": "descripción concreta",
      "priority": "high|medium|low"
    }
  ],

  "parity_issues": false,
  "distribution_health": "good|needs_attention|critical"
}
"""

import json
import asyncio
import anthropic
from datetime import datetime
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.agent_parse_utils import (
    parse_json_response,
    log_agent_parse_failure,
    MAX_RAW_LOG_CHARS,
)

AGENT_NAME = "distribution"


def _build_minimal_distribution_fallback(hotel_profile: dict, compset_data: dict) -> dict:
    """Dict mínimo válido cuando el LLM falla o devuelve JSON inválido."""
    return {
        "agent": "distribution",
        "hotel_name": hotel_profile.get("name", "?"),
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "confidence_score": 0.3,
        "confidence_notes": "Fallback: parse o API failure.",
        "visibility_score": 0.5,
        "visibility_label": "Fallback: datos insuficientes.",
        "booking_audit": {
            "search_position": 99,
            "search_position_percentile": "bottom_50pct",
            "genius_level": 0,
            "preferred_partner": False,
            "content_score_estimated": 0,
            "content_gaps": [],
            "cancellation_policy": "?",
            "response_rate_signals": "?",
        },
        "rate_parity": {"status": "ok", "issues_detected": [], "parity_issues": False},
        "google_hotels": {"visible": False, "position_estimated": 99, "free_booking_links_active": False},
        "channel_presence": {},
        "quick_wins": [],
        "seo_recommendations": [],
        "parity_issues": False,
        "distribution_health": "needs_attention",
    }


async def run_distribution_agent(
    hotel_profile: dict,
    compset_data: dict,
    api_key: str,
    model: str = "claude-opus-4-5",
) -> dict:
    """
    Ejecuta el Agente Distribution. Nunca lanza por JSON inválido/truncado;
    devuelve fallback mínimo si falla parse o API.
    """
    client = anthropic.Anthropic(api_key=api_key)
    user_prompt = _build_distribution_prompt(hotel_profile, compset_data)
    prompt_len = len(user_prompt)

    print(f"  [Agente Distribution] Auditando visibilidad de {hotel_profile.get('name','?')}...")

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
        return _build_minimal_distribution_fallback(hotel_profile, compset_data)

    if not raw:
        log_agent_parse_failure(AGENT_NAME, prompt_len, 0, "", "empty response")
        return _build_minimal_distribution_fallback(hotel_profile, compset_data)

    result, parse_error = parse_json_response(raw)
    if result is None:
        log_agent_parse_failure(
            AGENT_NAME, prompt_len, response_len,
            raw[:MAX_RAW_LOG_CHARS], parse_error or "parse failed",
        )
        return _build_minimal_distribution_fallback(hotel_profile, compset_data)

    visibility = result.get("visibility_score", "?")
    health = result.get("distribution_health", "?")
    parity = (result.get("rate_parity") or {}).get("status", "?")
    print(f"  [Agente Distribution] Visibilidad: {visibility} | Salud: {health} | Paridad: {parity}")
    return result


def _build_distribution_prompt(hotel_profile: dict, compset_data: dict) -> str:
    name = hotel_profile.get("name", "?")
    channels = hotel_profile.get("channels", {})
    ota = hotel_profile.get("ota_visibility", {})
    booking_pos = ota.get("booking_search_position", "?")
    genius = channels.get("booking", {}).get("genius_level", "?")
    preferred = channels.get("booking", {}).get("preferred_partner", False)
    booking_score = hotel_profile.get("reputation", {}).get("booking_score", "?")

    primary = compset_data.get("compset", {}).get("primary", [])
    compset_channels = "\n".join([
        f"  - {h.get('name','?')}: canales {', '.join(h.get('channels',[]))}"
        for h in primary[:5]
    ])

    return f"""Audita la distribución y visibilidad de:

HOTEL: {name}
Posición en Booking búsqueda ciudad: #{booking_pos}
Genius Level: {genius} | Preferred Partner: {preferred}
Score Booking: {booking_score}
Canales activos: {list(channels.keys())}

DISTRIBUCIÓN DEL COMPSET:
{compset_channels if compset_channels else '  (sin datos)'}

Fecha: {datetime.now().strftime('%Y-%m-%d')}
Devuelve ÚNICAMENTE el JSON estructurado.
"""
