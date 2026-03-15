"""
RevMax — Agente 3: Pricing Intelligence
=========================================
Experto en pricing dinámico hotelero · yield management · índices STR
Especialidad: Duetto, IDeaS, OTA Insight · Cadenas: Marriott, Hilton, IHG

Este agente calcula los índices profesionales de pricing (MPI, ARI, RGI),
evalúa el posicionamiento de precio por tipo de habitación, detecta
oportunidades de yield y emite recomendaciones con límites de seguridad.

CONTEXTO SIN PMS:
Sin acceso al PMS, el agente trabaja con proxies de ocupación basados en
la disponibilidad del compset. Esta es la técnica estándar que usan los
revenue managers independientes para hoteles sin RMS conectado.
"""

AGENT_SYSTEM_PROMPT = """
Eres el Agente Pricing de RevMax, un experto en pricing dinámico hotelero con
15 años de experiencia implementando estrategias de revenue management en
sistemas como Duetto, IDeaS G3 y OTA Insight. Has trabajado con cadenas
Marriott, Hilton e IHG y con hoteles independientes de lujo en Europa y LATAM.

Tu misión es evaluar el posicionamiento de precio del hotel vs su compset,
calcular los índices profesionales de la industria y emitir recomendaciones
de precio accionables, específicas y con justificación de negocio.

════════════════════════════════════════════════════════════
ÍNDICES PROFESIONALES — DEFINICIÓN Y USO
════════════════════════════════════════════════════════════

MPI — Market Penetration Index
  MPI = Ocupación_hotel / Ocupación_mercado
  - MPI > 1.0: el hotel capta más cuota de mercado que la media del compset
  - MPI < 1.0: el mercado supera al hotel en ocupación
  - SIN PMS: proxy = (habitaciones_no_disponibles_competencia / total_competencia)
  - Interpretación crítica: MPI alto + precio bajo = estás dejando dinero.
    MPI bajo + precio alto = estás espantando clientes.

ARI — Average Rate Index
  ARI = ADR_hotel / ADR_compset_primario
  - ARI > 1.0: cobras más que el mercado
  - ARI < 1.0: cobras menos que el mercado
  - ARI ideal para hotel de calidad superior: 1.05–1.20
  - ARI ideal para hotel equivalente al compset: 0.95–1.05
  - ARI < 0.85: precio peligrosamente bajo — señal de problema estratégico
  - ARI > 1.30: precio arriesgado — necesita justificación clara (reputación, evento)

RGI — Revenue Generation Index
  RGI = MPI × ARI (o equivalente: RevPAR_hotel / RevPAR_mercado)
  - RGI > 1.0: el hotel genera más revenue por habitación disponible que el mercado
  - RGI < 1.0: el mercado supera al hotel en eficiencia de revenue
  - RGI es el KPI definitivo del revenue manager
  - Meta razonable para hotel bien gestionado: RGI entre 1.0 y 1.15

BARI — Best Available Rate Index
  Compara tu BAR (mejor tarifa disponible) vs BAR del compset
  Útil para detectar si estás posicionado correctamente en el canal OTA

════════════════════════════════════════════════════════════
METODOLOGÍA DE RECOMENDACIÓN DE PRECIO
════════════════════════════════════════════════════════════

PASO 1 — DIAGNÓSTICO DE POSICIÓN
  Clasifica al hotel en una de estas 4 situaciones:

  A) LÍDER: ARI > 1.0 Y MPI > 1.0 → Demanda fuerte y precio premium
     Acción: mantener o subida moderada (+5–10%). Monitorear diariamente.

  B) VOLUMEN: ARI < 1.0 Y MPI > 1.0 → Captura demanda con precio bajo
     Acción: subida progresiva (+8–15%). Estás dejando revenue.

  C) PREMIUM EN RIESGO: ARI > 1.0 Y MPI < 1.0 → Precio alto, baja ocupación
     Acción: analizar causa. Si es por segmento o calidad, mantener.
     Si es por precio, bajar (-5–12%) o lanzar tarifa early bird.

  D) REZAGADO: ARI < 1.0 Y MPI < 1.0 → Precio bajo Y baja ocupación
     Acción: no bajar más. El problema no es el precio — revisar
     distribución, reputación o producto. Posible promo flash.

PASO 2 — ANÁLISIS POR TIPO DE HABITACIÓN
  Cada tipo de habitación es un producto diferente con su propio mercado.
  Reglas de yield por categoría:
  - Habitación estándar: ancla de precio. Debe ser competitiva siempre.
  - Superior/Deluxe: upsell principal. Diferencial óptimo: +20–35% vs estándar.
  - Suite: producto de nicho. Diferencial óptimo: +80–150% vs estándar.
  - Familiar: demanda inelástica en temporada escolar. Puede subirse más en verano.

PASO 3 — REGLAS DE MOVIMIENTO DE PRECIO (CRÍTICO)
  Nunca mover precio más de un 15% en una sola decisión.
  El mercado tarda 48–72h en reaccionar. Medir antes de volver a mover.

  Movimientos permitidos por señal:
  - Demanda muy alta (compset >85% lleno): +10–15%
  - Demanda alta (compset 70–85% lleno): +5–10%
  - Demanda media (compset 50–70% lleno): 0% a +5%
  - Demanda baja (compset <50% lleno): -5% a -10%
  - Evento local confirmado: +15% adicional sobre la regla de demanda
  - Promoción activa en >3 competidores: considerar promo flash 24–48h

PASO 4 — DETECCIÓN DE OPORTUNIDADES DE YIELD
  Revisar siempre:
  - Length of stay: ¿hay restricciones de mínimo de noches que aplicar?
  - Last minute: ¿queda disponibilidad 0–3 días vista? → tarifa last minute
  - Early bird: ¿baja ocupación 30+ días vista? → descuento early bird
  - Non-refundable: ¿el compset ofrece NRF más agresivo? → revisar diferencial

════════════════════════════════════════════════════════════
FORMATO DE OUTPUT — JSON ESTRUCTURADO
════════════════════════════════════════════════════════════

Devuelve SIEMPRE este JSON exacto, sin texto adicional:

{
  "agent": "pricing",
  "hotel_name": "nombre del hotel",
  "analysis_date": "YYYY-MM-DD",
  "confidence_score": 0.0-1.0,
  "confidence_notes": "razón del confidence",

  "indices": {
    "ari": {
      "value": 0.96,
      "interpretation": "Por debajo del mercado un 4%",
      "signal": "below|at|above",
      "target_range": [0.95, 1.10]
    },
    "mpi": {
      "value": 1.08,
      "interpretation": "Captando un 8% más de demanda que el compset",
      "signal": "below|at|above",
      "source": "proxy_compset_availability|pms_direct",
      "proxy_methodology": "descripción de cómo se calculó sin PMS"
    },
    "rgi": {
      "value": 1.04,
      "interpretation": "Generando un 4% más de revenue por habitación disponible que el mercado",
      "signal": "below|at|above",
      "vs_target": "on_track|underperforming|outperforming"
    },
    "bari": {
      "value": 0.94,
      "your_bar": 145.0,
      "market_bar": 154.0
    }
  },

  "position_diagnosis": {
    "quadrant": "A_leader|B_volume|C_premium_risk|D_laggard",
    "quadrant_label": "Líder de mercado",
    "summary": "descripción ejecutiva de la situación"
  },

  "room_type_analysis": [
    {
      "type": "Doble Estándar",
      "your_price": 145.0,
      "market_avg": 154.0,
      "market_min": 112.0,
      "market_max": 198.0,
      "ari_room": 0.94,
      "recommended_price": 158.0,
      "change_pct": 8.9,
      "change_direction": "raise|hold|lower",
      "max_safe_change_pct": 15.0,
      "yield_opportunity": "upsell|last_minute|early_bird|los_restriction|none",
      "justification": "razón específica de negocio para el cambio"
    }
  ],

  "recommendation": {
    "action": "raise|hold|lower|promo",
    "urgency": "immediate|this_week|monitor",
    "primary_action": "descripción concreta: qué hacer, cuánto, cuándo",
    "secondary_action": "acción complementaria si la hay",
    "expected_impact": "impacto estimado en revenue (+X% RevPAR esperado)",
    "review_in_hours": 48
  },

  "yield_opportunities": [
    {
      "type": "early_bird|last_minute|non_refundable|minimum_stay|package",
      "description": "descripción concreta de la oportunidad",
      "suggested_discount_or_premium": 12.0,
      "applicable_room_types": ["Doble Estándar"],
      "applicable_dates": "próximos 7 días|fin de semana|+30 días",
      "estimated_revenue_impact": "descripción del impacto"
    }
  ],

  "pricing_alerts": [
    {
      "level": "high|medium|low",
      "type": "rate_parity|underpricing|overpricing|competitor_promo",
      "description": "descripción del alerta",
      "action_required": true
    }
  ],

  "market_context": {
    "compset_avg_adr": 154.0,
    "compset_min_adr": 112.0,
    "compset_max_adr": 198.0,
    "your_position_rank": 3,
    "total_compset": 6,
    "promotions_in_compset": 2,
    "estimated_market_occupancy_pct": 72.0
  },

  "pms_upgrade_note": "Con acceso al PMS podríamos calcular: RevPAR real, pickup rate, pace vs LY. Actualmente usamos proxies de disponibilidad del compset."
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

AGENT_NAME = "pricing"


def _calculate_proxy_indices(hotel_profile: dict, compset_data: dict) -> dict:
    """
    Calcula MPI, ARI y RGI usando proxies públicos.
    Esta función extrae lo que puede calcularse matemáticamente
    antes de llamar al LLM, para mejorar la precisión.
    """
    your_adr = hotel_profile.get("adr_double") or 0
    summary = compset_data.get("compset_summary", {})
    market_avg = summary.get("primary_avg_adr") or 0
    market_min = summary.get("primary_min_adr") or 0
    market_max = summary.get("primary_max_adr") or 0

    # ARI — calculable directamente
    ari = round(your_adr / market_avg, 3) if market_avg else None

    # MPI proxy — basado en disponibilidad del compset
    # Si el compset tiene poca disponibilidad = demanda alta = MPI probablemente alto
    primary = compset_data.get("compset", {}).get("primary", [])
    promo_count = sum(1 for h in primary if h.get("promotions_active"))
    promo_ratio = promo_count / len(primary) if primary else 0

    # Proxy: muchas promos en compset = demanda baja = MPI tendencialmente bajo
    mpi_proxy = 1.0
    if promo_ratio > 0.5:
        mpi_proxy = 0.85
    elif promo_ratio > 0.3:
        mpi_proxy = 0.95
    elif promo_ratio == 0:
        mpi_proxy = 1.05

    rgi = round(ari * mpi_proxy, 3) if ari else None

    # Posición por precio
    your_rank = sum(1 for h in primary if h.get("adr_double", 0) < your_adr) + 1

    return {
        "ari_calculated": ari,
        "mpi_proxy": mpi_proxy,
        "rgi_estimated": rgi,
        "market_avg": market_avg,
        "market_min": market_min,
        "market_max": market_max,
        "your_rank": your_rank,
        "total_primary": len(primary),
        "promo_count": promo_count,
        "promo_ratio": promo_ratio,
    }


def _build_minimal_pricing_fallback(
    hotel_profile: dict,
    compset_data: dict,
    demand_data: dict,
) -> dict:
    """Dict mínimo válido cuando el LLM falla o devuelve JSON inválido."""
    pre = _calculate_proxy_indices(hotel_profile, compset_data)
    summary = compset_data.get("compset_summary", {})
    market_avg = summary.get("primary_avg_adr") or pre.get("market_avg") or 100.0
    return {
        "agent": "pricing",
        "hotel_name": hotel_profile.get("name", "?"),
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "confidence_score": 0.3,
        "confidence_notes": "Fallback: parse o API failure.",
        "indices": {
            "ari": {"value": pre.get("ari_calculated") or 1.0, "interpretation": "Fallback", "signal": "at", "target_range": [0.95, 1.10]},
            "mpi": {"value": pre.get("mpi_proxy") or 1.0, "interpretation": "Fallback", "signal": "at", "source": "proxy_compset_availability"},
            "rgi": {"value": pre.get("rgi_estimated") or 1.0, "interpretation": "Fallback", "signal": "at", "vs_target": "on_track"},
            "bari": {"value": 1.0, "your_bar": 0, "market_bar": 0},
        },
        "position_diagnosis": {"quadrant": "B_volume", "quadrant_label": "Datos insuficientes", "summary": "Fallback por fallo de parse o API."},
        "room_type_analysis": [],
        "recommendation": {
            "action": "hold",
            "urgency": "monitor",
            "primary_action": "Mantener precio. Datos insuficientes.",
            "secondary_action": "",
            "expected_impact": "",
            "review_in_hours": 48,
        },
        "yield_opportunities": [],
        "pricing_alerts": [],
        "market_context": {
            "compset_avg_adr": market_avg,
            "compset_min_adr": pre.get("market_min") or 80,
            "compset_max_adr": pre.get("market_max") or 120,
            "your_position_rank": pre.get("your_rank") or 5,
            "total_compset": pre.get("total_primary") or 5,
            "promotions_in_compset": pre.get("promo_count") or 0,
            "estimated_market_occupancy_pct": 50.0,
        },
        "pms_upgrade_note": "Fallback: sin análisis LLM.",
    }


async def run_pricing_agent(
    hotel_profile: dict,
    compset_data: dict,
    demand_data: dict,
    api_key: str,
    model: str = "claude-opus-4-5",
) -> dict:
    """
    Ejecuta el Agente Pricing. Nunca lanza por JSON inválido/truncado;
    devuelve fallback mínimo si falla parse o API.
    """
    client = anthropic.Anthropic(api_key=api_key)
    pre_calculated = _calculate_proxy_indices(hotel_profile, compset_data)
    user_prompt = _build_pricing_prompt(hotel_profile, compset_data, demand_data, pre_calculated)
    prompt_len = len(user_prompt)

    print(f"  [Agente Pricing] Calculando índices MPI/ARI/RGI para {hotel_profile.get('name', '?')}...")
    print(f"  [Agente Pricing] ARI calculado: {pre_calculated['ari_calculated']} | MPI proxy: {pre_calculated['mpi_proxy']}")

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
        return _build_minimal_pricing_fallback(hotel_profile, compset_data, demand_data)

    if not raw:
        log_agent_parse_failure(AGENT_NAME, prompt_len, 0, "", "empty response")
        return _build_minimal_pricing_fallback(hotel_profile, compset_data, demand_data)

    result, parse_error = parse_json_response(raw)
    if result is None:
        log_agent_parse_failure(
            AGENT_NAME, prompt_len, response_len,
            raw[:MAX_RAW_LOG_CHARS], parse_error or "parse failed",
        )
        return _build_minimal_pricing_fallback(hotel_profile, compset_data, demand_data)

    quadrant = result.get("position_diagnosis", {}).get("quadrant", "?")
    action = result.get("recommendation", {}).get("action", "?")
    rgi = result.get("indices", {}).get("rgi", {}).get("value", "?")
    print(f"  [Agente Pricing] Cuadrante: {quadrant} | RGI: {rgi} | Acción: {action.upper() if isinstance(action, str) else '?'}")
    return result


def _build_pricing_prompt(
    hotel_profile: dict,
    compset_data: dict,
    demand_data: dict,
    pre_calc: dict,
) -> str:

    name = hotel_profile.get("name", "?")
    your_adr = hotel_profile.get("adr_double", "?")
    stars = hotel_profile.get("stars", "?")
    segment = hotel_profile.get("primary_segment", "?")
    room_types = hotel_profile.get("room_types", [])

    summary = compset_data.get("compset_summary", {})
    position = summary.get("your_position", "?")
    primary = compset_data.get("compset", {}).get("primary", [])

    demand_signal = demand_data.get("demand_index", {}).get("signal", "medium")
    demand_score = demand_data.get("demand_index", {}).get("score", 50)
    events = demand_data.get("events_detected", [])

    compset_detail = "\n".join([
        f"  {i+1}. {h.get('name','?')} | {h.get('adr_double','?')}€ | "
        f"Score:{h.get('booking_score','?')} | "
        f"{'PROMO ACTIVA' if h.get('promotions_active') else 'sin promo'}"
        for i, h in enumerate(primary[:8])
    ])

    room_types_text = "\n".join([
        f"  - {r.get('type','?')}: {r.get('min_price','?')}€ – {r.get('max_price','?')}€"
        for r in room_types
    ]) if room_types else "  (tipos de habitación no disponibles)"

    events_text = ", ".join(events) if events else "ninguno detectado"

    return f"""Realiza el análisis completo de pricing para:

HOTEL ANALIZADO:
  Nombre: {name}
  Estrellas: {stars}★ | Segmento: {segment}
  ADR habitación doble estándar: {your_adr}€
  Posición declarada vs compset: {position}

TIPOS DE HABITACIÓN Y PRECIOS ACTUALES:
{room_types_text}

COMPSET PRIMARIO ({len(primary)} hoteles):
{compset_detail if compset_detail else "  (sin datos de compset primario)"}

ÍNDICES PRE-CALCULADOS (usa estos datos exactos):
  ARI calculado: {pre_calc['ari_calculated']}
  MPI proxy (basado en disponibilidad compset): {pre_calc['mpi_proxy']}
  RGI estimado: {pre_calc['rgi_estimated']}
  Media mercado: {pre_calc['market_avg']}€
  Mín. mercado: {pre_calc['market_min']}€
  Máx. mercado: {pre_calc['market_max']}€
  Tu posición por precio: #{pre_calc['your_rank']} de {pre_calc['total_primary']}
  Hoteles en compset con promo activa: {pre_calc['promo_count']} de {pre_calc['total_primary']}

SEÑAL DE DEMANDA (Agente 4):
  Señal: {demand_signal.upper()} (score: {demand_score}/100)
  Eventos detectados: {events_text}

INSTRUCCIONES:
1. Usa los índices pre-calculados como base — puedes refinarlos si tienes información adicional.
2. Analiza cada tipo de habitación por separado aplicando las reglas de yield.
3. La recomendación de precio NUNCA debe superar el 15% de cambio en una sola decisión.
4. Si hay promociones en >30% del compset, evalúa si corresponde una promo flash.
5. Devuelve ÚNICAMENTE el JSON estructurado.
6. Fecha de análisis: {datetime.now().strftime('%Y-%m-%d')}
"""


if __name__ == "__main__":
    import os

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: define ANTHROPIC_API_KEY")
        sys.exit(1)

    # Cargar outputs de agentes anteriores si existen
    def load_json(path, default):
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return default

    profile = load_json("data/agents/discovery_output.json", {
        "name": "Hotel Casa Fuster",
        "stars": 5,
        "primary_segment": "leisure",
        "adr_double": 320.0,
        "room_types": [
            {"type": "Doble Estándar", "min_price": 280.0, "max_price": 420.0},
            {"type": "Junior Suite", "min_price": 480.0, "max_price": 650.0},
        ],
    })

    compset = load_json("data/agents/compset_output.json", {
        "compset_summary": {
            "primary_avg_adr": 335.0,
            "primary_min_adr": 220.0,
            "primary_max_adr": 495.0,
            "your_position": "below_market",
            "market_pressure": "raise",
        },
        "compset": {"primary": [
            {"name": "Hotel Majestic", "adr_double": 340.0, "booking_score": 8.8, "promotions_active": False},
            {"name": "Hotel Omm", "adr_double": 290.0, "booking_score": 8.9, "promotions_active": False},
            {"name": "El Palace", "adr_double": 480.0, "booking_score": 9.2, "promotions_active": False},
        ]},
    })

    demand_stub = {
        "demand_index": {"score": 68, "signal": "medium"},
        "events_detected": [],
    }

    print("\nRevMax — Test Agente 3: Pricing Intelligence")
    print("=" * 50)

    result = asyncio.run(run_pricing_agent(profile, compset, demand_stub, api_key))

    print("\n── OUTPUT DEL AGENTE ──────────────────────────")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    os.makedirs("data/agents", exist_ok=True)
    path = "data/agents/pricing_output.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n✓ Resultado guardado en {path}")
