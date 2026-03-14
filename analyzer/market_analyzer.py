"""
RevMax — Motor de análisis
Compara tu hotel con la competencia y genera insights estructurados.
"""

import json
import statistics
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class HotelConfig:
    """Configuración de tu hotel. Edita config.json para personalizar."""
    name: str                          # Nombre EXACTO como aparece en Booking
    city: str                          # Ciudad
    stars: int                         # Número de estrellas
    room_types: list[str]              # Tipos de habitación que tienes
    base_prices: dict[str, float]      # Precios base por tipo: {"doble": 120, "suite": 200}
    competitor_names: list[str]        # Lista de competidores a vigilar (nombres parciales)
    target_occupancy: float = 0.80     # Ocupación objetivo (80%)
    min_price: float = 60.0            # Precio mínimo absoluto
    max_price: float = 500.0           # Precio máximo absoluto


@dataclass
class CompetitorInsight:
    name: str
    price: float
    review_score: Optional[float]
    stars: Optional[int]
    price_diff_pct: float              # % diferencia vs tu precio
    is_cheaper: bool
    is_promotion: bool                 # Precio sospechosamente bajo = posible promo


@dataclass
class PriceRecommendation:
    room_type: str
    current_price: float
    recommended_price: float
    change_pct: float
    reason: str
    urgency: str                       # "alta" | "media" | "baja"


@dataclass
class DailyAnalysis:
    date: str
    hotel_name: str
    city: str

    # Posición en mercado
    your_avg_price: float
    market_avg_price: float
    market_min_price: float
    market_max_price: float
    your_position_rank: int            # Posición por precio (1 = más barato)
    total_competitors: int

    # Insights de competencia
    competitors: list[CompetitorInsight]
    promotions_detected: list[str]     # Nombres de hoteles con promos activas

    # Recomendaciones
    recommendations: list[PriceRecommendation]

    # Señales del mercado
    demand_signal: str                 # "alta" | "media" | "baja"
    demand_reason: str
    price_pressure: str                # "subir" | "mantener" | "bajar"

    # Scores de posición
    competitiveness_score: float       # 0-10
    opportunity_score: float           # 0-10, cuánto dinero estás dejando en la mesa


def load_prices(path: str = "data/prices_latest.json") -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config(path: str = "config.json") -> HotelConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return HotelConfig(**data)


def detect_promotion(price: float, market_avg: float) -> bool:
    """Un precio >25% por debajo de la media del mercado sugiere promoción."""
    if not price or not market_avg:
        return False
    return price < market_avg * 0.75


def analyze_market(prices_data: list[dict], config: HotelConfig) -> DailyAnalysis:
    """
    Análisis completo del mercado.
    Compara tu hotel con todos los resultados del scraper.
    """

    # Filtrar precios válidos
    valid = [h for h in prices_data if h.get("price") and h["price"] > 10]

    if not valid:
        raise ValueError("No hay datos de precios válidos para analizar")

    all_prices = [h["price"] for h in valid]
    market_avg = statistics.mean(all_prices)
    market_min = min(all_prices)
    market_max = max(all_prices)

    # Encontrar tu hotel en los resultados
    your_hotel = None
    for h in valid:
        if config.name.lower() in h["name"].lower():
            your_hotel = h
            break

    # Si no encontramos el hotel exacto, usar precio base de config
    your_price = your_hotel["price"] if your_hotel else list(config.base_prices.values())[0]
    your_avg_price = your_price

    # Posición por precio
    cheaper_count = sum(1 for p in all_prices if p < your_price)
    rank = cheaper_count + 1  # rank 1 = más barato

    # Análisis de competidores
    competitors = []
    promotions = []

    for h in valid:
        if config.name.lower() in h["name"].lower():
            continue  # Saltar tu propio hotel

        # ¿Es un competidor vigilado?
        is_watched = any(
            comp.lower() in h["name"].lower()
            for comp in config.competitor_names
        )

        diff_pct = ((h["price"] - your_price) / your_price) * 100
        is_promo = detect_promotion(h["price"], market_avg)

        if is_promo:
            promotions.append(h["name"])

        if is_watched or abs(diff_pct) < 30:  # Incluir hoteles con precio similar
            competitors.append(CompetitorInsight(
                name=h["name"],
                price=h["price"],
                review_score=h.get("review_score"),
                stars=h.get("stars"),
                price_diff_pct=diff_pct,
                is_cheaper=h["price"] < your_price,
                is_promotion=is_promo,
            ))

    # Ordenar competidores: primero los que tienen promo, luego por precio
    competitors.sort(key=lambda c: (not c.is_promotion, c.price))
    competitors = competitors[:10]  # Top 10 más relevantes

    # Señal de demanda (heurística basada en precios del mercado)
    price_vs_usual = market_avg / (sum(config.base_prices.values()) / len(config.base_prices))
    if price_vs_usual > 1.15:
        demand_signal = "alta"
        demand_reason = f"Los precios del mercado están un {(price_vs_usual-1)*100:.0f}% por encima de lo habitual"
    elif price_vs_usual < 0.90:
        demand_signal = "baja"
        demand_reason = f"Los precios del mercado están un {(1-price_vs_usual)*100:.0f}% por debajo de lo habitual"
    else:
        demand_signal = "media"
        demand_reason = "Precios del mercado en niveles normales"

    # Presión de precio
    cheaper_ratio = sum(1 for p in all_prices if p < your_price) / len(all_prices)
    if cheaper_ratio > 0.6:
        price_pressure = "bajar"
    elif cheaper_ratio < 0.3:
        price_pressure = "subir"
    else:
        price_pressure = "mantener"

    # Recomendaciones por tipo de habitación
    recommendations = []
    for room_type, base_price in config.base_prices.items():
        rec_price = base_price

        if demand_signal == "alta" and price_pressure in ("subir", "mantener"):
            rec_price = base_price * 1.12
            reason = f"Demanda alta detectada en el mercado. Subida del 12% recomendada."
            urgency = "alta"
        elif promotions and price_pressure == "bajar":
            rec_price = base_price * 0.92
            reason = f"{len(promotions)} competidores con promociones activas. Considera oferta temporal."
            urgency = "media"
        elif price_pressure == "subir" and cheaper_ratio < 0.25:
            rec_price = base_price * 1.08
            reason = f"Eres de los más baratos del mercado ({rank}º posición). Margen para subir precio."
            urgency = "media"
        else:
            reason = "Precio competitivo. Mantener posición actual."
            urgency = "baja"

        change_pct = ((rec_price - base_price) / base_price) * 100

        # Aplicar límites
        rec_price = max(config.min_price, min(config.max_price, rec_price))

        recommendations.append(PriceRecommendation(
            room_type=room_type,
            current_price=base_price,
            recommended_price=round(rec_price, 0),
            change_pct=round(change_pct, 1),
            reason=reason,
            urgency=urgency,
        ))

    # Scores
    competitiveness_score = round(10 - (rank / len(valid)) * 10, 1)
    opportunity_score = round(min(10, abs(change_pct) * 2) if recommendations else 0, 1)
    change_pct = recommendations[0].change_pct if recommendations else 0

    return DailyAnalysis(
        date=datetime.now().strftime("%Y-%m-%d"),
        hotel_name=config.name,
        city=config.city,
        your_avg_price=your_avg_price,
        market_avg_price=round(market_avg, 2),
        market_min_price=round(market_min, 2),
        market_max_price=round(market_max, 2),
        your_position_rank=rank,
        total_competitors=len(valid),
        competitors=competitors,
        promotions_detected=promotions,
        recommendations=recommendations,
        demand_signal=demand_signal,
        demand_reason=demand_reason,
        price_pressure=price_pressure,
        competitiveness_score=competitiveness_score,
        opportunity_score=round(min(10, abs(change_pct) * 2), 1),
    )


if __name__ == "__main__":
    import sys
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    prices_path = sys.argv[2] if len(sys.argv) > 2 else "data/prices_latest.json"

    config = load_config(config_path)
    prices = load_prices(prices_path)
    analysis = analyze_market(prices, config)

    print(f"\nAnálisis para {analysis.hotel_name}")
    print(f"Tu precio: {analysis.your_avg_price}€ | Media mercado: {analysis.market_avg_price}€")
    print(f"Posición: #{analysis.your_position_rank} de {analysis.total_competitors}")
    print(f"Demanda: {analysis.demand_signal.upper()} — {analysis.demand_reason}")
    print(f"\nRecomendaciones:")
    for r in analysis.recommendations:
        arrow = "↑" if r.change_pct > 0 else ("↓" if r.change_pct < 0 else "→")
        print(f"  {r.room_type}: {r.current_price}€ {arrow} {r.recommended_price}€ ({r.change_pct:+.1f}%) [{r.urgency}]")
        print(f"    {r.reason}")
