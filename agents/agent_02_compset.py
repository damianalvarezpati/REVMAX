"""
RevMax — Agente 2: Compset Intelligence
========================================
Revenue Manager Senior · 15 años en cadenas internacionales y hoteles independientes de lujo.

Este agente es el más crítico del sistema. Un compset mal definido contamina
todos los análisis posteriores. Su output es la base sobre la que trabajan
los agentes de Pricing, Demand, Reputation y Distribution.
"""

AGENT_SYSTEM_PROMPT = """
Eres el Agente Compset de RevMax, un Revenue Manager Senior con 15 años de experiencia
en cadenas hoteleras internacionales (Marriott, IHG, Four Seasons) y consultoría
independiente para hoteles boutique y de lujo.

Tu única misión es construir el competitive set más preciso y útil posible para un hotel,
usando únicamente datos públicos. Un compset excelente no es una lista de hoteles cercanos
— es una selección de establecimientos con los que el hotel compite REALMENTE por el mismo
cliente, en el mismo momento de decisión de compra.

════════════════════════════════════════════════════════════
METODOLOGÍA PROFESIONAL — CRITERIOS POR ORDEN DE IMPORTANCIA
════════════════════════════════════════════════════════════

CRITERIO 1 — ADR SIMILAR (peso: 30%)
El Average Daily Rate es el criterio principal. Si el precio es muy diferente,
el cliente no está comparando ambos hoteles. Regla:
  - Compset primario: ADR del candidato entre 75% y 125% del hotel analizado
  - Compset aspiracional: ADR entre 125% y 160% (aspirational set)
  - Excluir siempre: ADR por debajo del 70% o por encima del 175%
Matiz importante: comparar ADR de habitación equivalente (doble estándar vs doble estándar),
no precio de suite vs habitación estándar.

CRITERIO 2 — SEGMENTO DE DEMANDA PRIMARIO (peso: 25%)
¿A qué tipo de cliente sirve principalmente el hotel?
  - Leisure: turistas, familias, parejas, viajes de ocio
  - Business: viajeros de empresa, corporativo
  - MICE: grupos, congresos, eventos, bodas
  - Extended stay: estancias largas (+5 noches)
  - Mixed: combinación de segmentos
Un hotel leisure no compite con uno business aunque tengan el mismo precio y estén
a 50 metros, porque el cliente busca cosas diferentes en el momento de decisión.
Inferir el segmento desde: ubicación (centro ciudad vs polígono industrial vs resort),
amenities (spa vs sala de reuniones), políticas (cancelación flexible vs tarifa corporativa).

CRITERIO 3 — MICRO-MERCADO / UBICACIÓN FUNCIONAL (peso: 20%)
No es distancia en metros — es si comparten la misma "zona de demanda":
  - Centro histórico / zona turística
  - Distrito de negocios / CBD
  - Zona aeroportuaria
  - Periferia / polígono
  - Resort / playa / montaña
  - Suburbano / carretera
Dos hoteles en el mismo barrio pero en micro-mercados diferentes NO son compset.
Ejemplo: hotel en Paseo de Gracia (Barcelona) vs hotel en el Eixample a 400m —
pueden ser compset. Hotel en Paseo de Gracia vs hotel en Sants (mismo precio) — NO.

CRITERIO 4 — CATEGORÍA (peso: 15%)
Regla base: ±1 estrella. Matices:
  - Un hotel boutique 4★ con servicios premium puede competir con un 5★ de cadena grande
    si el ADR es similar y el segmento es el mismo.
  - Un 3★ de diseño en ubicación prime puede competir con 4★ estándar.
  - Nunca incluir más de 1 categoría de diferencia (un 3★ no compite con un 5★).
  - En ausencia de clasificación oficial, usar el ADR y los amenities como proxy.

CRITERIO 5 — TAMAÑO DEL ESTABLECIMIENTO (peso: 10%)
Un hotel de 15 habitaciones y uno de 500 no tienen el mismo comportamiento de precios
ni la misma capacidad de absorber demanda. Regla:
  - Compset ideal: mismo orden de magnitud de habitaciones (×0.4 a ×2.5)
  - Hoteles muy grandes pueden incluirse como referencia pero con peso reducido
  - Para hoteles pequeños (<50 hab), priorizar similitud de tamaño sobre otros criterios

════════════════════════════════════════════════════════════
ESTRUCTURA DEL COMPSET
════════════════════════════════════════════════════════════

El compset profesional tiene tres capas:

CAPA A — COMPSET PRIMARIO (5–7 hoteles)
Los competidores directos. Cumplen al menos 4 de los 5 criterios anteriores.
Son los hoteles con los que el cliente te compara directamente antes de reservar.
ESTOS son los que determinan tu precio óptimo día a día.

CAPA B — COMPSET ASPIRACIONAL (2–3 hoteles)
Hoteles de categoría o precio ligeramente superior (ADR +25% a +60%).
Son los hoteles a los que aspiras parecerte o con los que compites en temporada alta.
Útiles para detectar techos de precio y tendencias del mercado premium.

CAPA C — COMPSET DE VIGILANCIA (2–3 hoteles)
Hoteles de categoría inferior o disruptores (apartamentos de lujo, Airbnb premium).
Son los que pueden capturar demanda cuando estás caro o en temporada baja.
Útiles para detectar price floors y amenazas de sustitución.

════════════════════════════════════════════════════════════
SEÑALES DE EXCLUSIÓN — CUÁNDO NO INCLUIR UN HOTEL
════════════════════════════════════════════════════════════

Excluir siempre:
  - Hoteles con cierre temporal o reforma (señal: sin disponibilidad en múltiples fechas)
  - Hoteles que no están en OTAs (no son comparables para el cliente digital)
  - Hoteles con <10 reseñas (datos insuficientes para análisis de reputación)
  - Apartamentos vacacionales salvo que sean competencia real documentada
  - El propio hotel analizado (obvio pero importante validar)

════════════════════════════════════════════════════════════
FORMATO DE OUTPUT — JSON ESTRUCTURADO
════════════════════════════════════════════════════════════

Devuelve SIEMPRE este JSON exacto, sin texto adicional:

{
  "hotel_name": "nombre del hotel analizado",
  "analysis_date": "YYYY-MM-DD",
  "confidence_score": 0.0-1.0,
  "confidence_notes": "por qué el confidence es ese nivel",
  "primary_segment": "leisure|business|mice|extended_stay|mixed",
  "micro_market": "descripción de la zona funcional",
  "hotel_adr_reference": {
    "standard_double": precio_euros,
    "source": "booking|manual|estimado",
    "date_checked": "YYYY-MM-DD"
  },
  "compset": {
    "primary": [
      {
        "rank": 1,
        "name": "nombre hotel",
        "stars": 4,
        "adr_double": 145.0,
        "adr_index": 0.98,
        "segment_match": "leisure",
        "micro_market_match": true,
        "size_rooms": 85,
        "size_match_score": 0.9,
        "booking_score": 8.4,
        "booking_reviews": 1240,
        "distance_km": 0.3,
        "inclusion_reason": "ADR similar, mismo segmento leisure, mismo micro-mercado centro, tamaño comparable",
        "channels": ["booking", "expedia", "google_hotels"],
        "genius_level": 2,
        "booking_url": "https://...",
        "last_price_checked": 145.0,
        "promotions_active": false
      }
    ],
    "aspirational": [...],
    "surveillance": [...]
  },
  "compset_summary": {
    "primary_avg_adr": 148.0,
    "primary_min_adr": 112.0,
    "primary_max_adr": 189.0,
    "your_position": "below_market|at_market|above_market",
    "your_adr_index": 0.96,
    "market_pressure": "raise|hold|lower",
    "notes": "observaciones clave del revenue manager"
  },
  "exclusions": [
    {
      "name": "Hotel Ejemplo",
      "reason": "ADR demasiado bajo (58% del tuyo) — segmento diferente"
    }
  ],
  "seasonal_notes": "consideraciones estacionales relevantes para este compset",
  "next_review_trigger": "evento o condición que debería disparar una revisión del compset"
}

════════════════════════════════════════════════════════════
REGLAS DE COMPORTAMIENTO
════════════════════════════════════════════════════════════

1. Nunca incluyas un hotel en el compset primario solo por proximidad geográfica.
   Justifica SIEMPRE la inclusión con criterios de negocio.

2. Si no puedes verificar el ADR de un candidato, marca su adr_index como null
   y el confidence_score baja automáticamente 0.1 puntos.

3. Si el hotel analizado está en una ciudad con menos de 20 hoteles comparables,
   amplía el radio geográfico antes de bajar el criterio de ADR.

4. En destinos de alta estacionalidad (más del 40% de variación de precio entre
   temporada alta y baja), nota en seasonal_notes que el compset puede cambiar
   entre temporadas.

5. Siempre incluye al menos 1 hotel en el compset de vigilancia que sea
   un apartamento de lujo o Airbnb Plus si existe en la zona — son la
   amenaza de sustitución más creciente del sector.

6. El campo next_review_trigger debe ser específico: "Apertura del hotel X
   prevista para Q3 2025" o "Revisión recomendada en temporada alta (julio)"
   — nunca genérico como "revisar periódicamente".
"""

# ─────────────────────────────────────────────────────────
# LÓGICA DEL AGENTE
# ─────────────────────────────────────────────────────────

import json
import asyncio
import anthropic
from datetime import datetime
from typing import Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.agent_parse_utils import (
    parse_json_response,
    log_agent_parse_failure,
    MAX_RAW_LOG_CHARS,
)

AGENT_NAME = "compset"


def _build_minimal_compset_fallback(hotel_profile: dict, market_data: dict) -> dict:
    """Dict mínimo válido cuando el LLM falla o devuelve JSON inválido."""
    name = hotel_profile.get("name", "Hotel")
    adr = hotel_profile.get("adr_double")
    if adr is None or (isinstance(adr, str) and adr == "?"):
        adr = 100.0
    elif not isinstance(adr, (int, float)):
        adr = 100.0
    return {
        "hotel_name": name,
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "confidence_score": 0.3,
        "confidence_notes": "Fallback: parse o API failure.",
        "primary_segment": hotel_profile.get("primary_segment", "mixed"),
        "micro_market": "?",
        "hotel_adr_reference": {"standard_double": adr, "source": "fallback", "date_checked": datetime.now().strftime("%Y-%m-%d")},
        "compset": {"primary": [], "aspirational": [], "surveillance": []},
        "compset_summary": {
            "primary_avg_adr": float(adr),
            "primary_min_adr": round(float(adr) * 0.8, 1),
            "primary_max_adr": round(float(adr) * 1.2, 1),
            "your_position": "at_market",
            "your_adr_index": 1.0,
            "market_pressure": "hold",
            "notes": "Fallback: sin datos de compset.",
        },
        "exclusions": [],
        "seasonal_notes": "",
        "next_review_trigger": "Revisar cuando haya datos de mercado.",
    }


async def run_compset_agent(
    hotel_profile: dict,
    market_data: dict,
    api_key: str,
    model: str = "claude-opus-4-5",
) -> dict:
    """
    Ejecuta el Agente Compset. Nunca lanza por JSON inválido/truncado;
    devuelve fallback mínimo si falla parse o API.
    """
    client = anthropic.Anthropic(api_key=api_key)
    user_prompt = _build_compset_prompt(hotel_profile, market_data)
    prompt_len = len(user_prompt)
    candidates_count = len(market_data.get("candidates", []))

    print(f"  [Agente Compset] Analizando {candidates_count} candidatos...")

    raw = ""
    response_len = 0
    try:
        response = client.messages.create(
            model=model,
            max_tokens=2000,
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
        return _build_minimal_compset_fallback(hotel_profile, market_data)

    if not raw:
        log_agent_parse_failure(AGENT_NAME, prompt_len, 0, "", "empty response")
        return _build_minimal_compset_fallback(hotel_profile, market_data)

    result, parse_error = parse_json_response(raw)
    if result is None:
        log_agent_parse_failure(
            AGENT_NAME, prompt_len, response_len,
            raw[:MAX_RAW_LOG_CHARS], parse_error or "parse failed",
        )
        return _build_minimal_compset_fallback(hotel_profile, market_data)

    print(f"  [Agente Compset] Compset definido: "
          f"{len(result.get('compset', {}).get('primary', []))} primarios, "
          f"{len(result.get('compset', {}).get('aspirational', []))} aspiracionales, "
          f"{len(result.get('compset', {}).get('surveillance', []))} vigilancia")
    print(f"  [Agente Compset] Confidence: {result.get('confidence_score', '?')}")
    return result


def _build_compset_prompt(hotel_profile: dict, market_data: dict) -> str:
    """Construye el prompt con los datos del hotel y candidatos del mercado."""

    name = hotel_profile.get("name", "desconocido")
    stars = hotel_profile.get("stars", "?")
    city = hotel_profile.get("city", "?")
    zone = hotel_profile.get("zone", "?")
    segment = hotel_profile.get("primary_segment", "?")
    adr = hotel_profile.get("adr_double", "?")
    rooms = hotel_profile.get("total_rooms", "?")
    score = hotel_profile.get("booking_score", "?")
    channels = hotel_profile.get("channels", [])

    candidates = market_data.get("candidates", [])
    candidates_text = "\n".join([
        f"  - {h.get('name', '?')} | {h.get('stars','?')}★ | "
        f"ADR doble: {h.get('adr_double','?')}€ | "
        f"Score: {h.get('booking_score','?')} ({h.get('booking_reviews','?')} reviews) | "
        f"Hab: {h.get('total_rooms','?')} | "
        f"Dist: {h.get('distance_km','?')}km | "
        f"Zona: {h.get('zone','?')} | "
        f"Canales: {', '.join(h.get('channels', []))}"
        for h in candidates
    ])

    return f"""Construye el compset para el siguiente hotel:

HOTEL ANALIZADO:
  Nombre: {name}
  Estrellas: {stars}★
  Ciudad: {city}
  Zona/Micro-mercado: {zone}
  Segmento primario detectado: {segment}
  ADR habitación doble estándar: {adr}€
  Total habitaciones: {rooms}
  Score Booking: {score}
  Canales activos: {', '.join(channels) if channels else 'por determinar'}

CANDIDATOS DISPONIBLES EN EL MERCADO ({len(candidates)} hoteles encontrados en el área):
{candidates_text if candidates_text else "  (sin datos de candidatos — usar conocimiento general del mercado)"}

INSTRUCCIONES:
1. Aplica los 5 criterios profesionales en el orden de importancia definido.
2. Clasifica cada hotel candidato en primario, aspiracional, vigilancia o exclusión.
3. Para cada hotel incluido, redacta una justificación específica de negocio (no genérica).
4. Si hay pocos candidatos válidos en el área, indícalo en confidence_notes y
   en seasonal_notes con recomendaciones para ampliar la búsqueda.
5. Devuelve ÚNICAMENTE el JSON estructurado según el formato definido.
6. Hoy es {datetime.now().strftime('%Y-%m-%d')}. Ten en cuenta la estación del año.
"""


# ─────────────────────────────────────────────────────────
# TEST STANDALONE
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os

    # Datos de ejemplo para probar el agente sin el sistema completo
    test_profile = {
        "name": "Hotel Casa Fuster",
        "stars": 5,
        "city": "Barcelona",
        "zone": "Passeig de Gràcia / Eixample",
        "primary_segment": "leisure",
        "adr_double": 320.0,
        "total_rooms": 105,
        "booking_score": 9.0,
        "channels": ["booking", "expedia", "google_hotels", "directo"]
    }

    test_market = {
        "candidates": [
            {"name": "Hotel Majestic", "stars": 5, "adr_double": 340.0, "booking_score": 8.8,
             "booking_reviews": 2100, "total_rooms": 271, "distance_km": 0.2,
             "zone": "Passeig de Gràcia", "channels": ["booking", "expedia"]},
            {"name": "El Palace Barcelona", "stars": 5, "adr_double": 480.0, "booking_score": 9.2,
             "booking_reviews": 1850, "total_rooms": 125, "distance_km": 0.4,
             "zone": "Passeig de Gràcia", "channels": ["booking", "directo"]},
            {"name": "Hotel Granados 83", "stars": 4, "adr_double": 180.0, "booking_score": 8.6,
             "booking_reviews": 890, "total_rooms": 77, "distance_km": 0.3,
             "zone": "Eixample", "channels": ["booking", "expedia"]},
            {"name": "Catalonia Eixample", "stars": 4, "adr_double": 130.0, "booking_score": 8.1,
             "booking_reviews": 3200, "total_rooms": 168, "distance_km": 0.5,
             "zone": "Eixample", "channels": ["booking", "expedia", "google_hotels"]},
            {"name": "Hotel Omm", "stars": 5, "adr_double": 290.0, "booking_score": 8.9,
             "booking_reviews": 1650, "total_rooms": 91, "distance_km": 0.3,
             "zone": "Passeig de Gràcia", "channels": ["booking", "directo"]},
            {"name": "Mandarin Oriental Barcelona", "stars": 5, "adr_double": 620.0,
             "booking_score": 9.4, "booking_reviews": 980, "total_rooms": 120,
             "distance_km": 0.2, "zone": "Passeig de Gràcia", "channels": ["booking", "directo"]},
            {"name": "Apartamentos Eixample Luxury", "stars": None, "adr_double": 210.0,
             "booking_score": 8.3, "booking_reviews": 340, "total_rooms": 18,
             "distance_km": 0.4, "zone": "Eixample", "channels": ["booking", "airbnb"]},
            {"name": "Hostal Grau", "stars": 2, "adr_double": 65.0, "booking_score": 7.8,
             "booking_reviews": 520, "total_rooms": 28, "distance_km": 0.8,
             "zone": "Raval", "channels": ["booking"]},
        ]
    }

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: Define la variable de entorno ANTHROPIC_API_KEY")
        sys.exit(1)

    print("\nRevMax — Test Agente 2: Compset Intelligence")
    print("=" * 50)
    print(f"Hotel: {test_profile['name']}")
    print(f"Candidatos: {len(test_market['candidates'])}")
    print()

    result = asyncio.run(run_compset_agent(test_profile, test_market, api_key))

    print("\n── OUTPUT DEL AGENTE ──────────────────────────")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # Guardar resultado
    os.makedirs("data/agents", exist_ok=True)
    path = "data/agents/compset_output.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n✓ Resultado guardado en {path}")
