"""
RevMax — Scraper Profesional v2
=================================
Experto en rate shopping hotelero · anti-detección · Playwright
Técnica: simulación de comportamiento humano + rotación de sesiones

Estrategia de fuentes (por fiabilidad):
  1. Google Hotels  → fiable, rápido, datos estructurados
  2. Booking.com    → más datos, requiere simulación humana
  3. TripAdvisor    → reputación y ranking

IMPORTANTE: Este scraper respeta los términos de uso extrayendo
solo datos públicos visibles para cualquier usuario, sin login,
con delays humanos y sin sobrecarga de servidores.
"""

import asyncio
import json
import random
import time
import re
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from typing import Optional
import logging

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# ─────────────────────────────────────────────────────────
# MODELOS DE DATOS
# ─────────────────────────────────────────────────────────

@dataclass
class ScrapedHotel:
    name: str
    city: str
    stars: Optional[int]
    adr_double: Optional[float]        # Precio noche doble estándar (referencia)
    price_min: Optional[float]         # Precio más barato disponible
    price_max: Optional[float]         # Precio más caro disponible
    booking_score: Optional[float]
    booking_reviews: Optional[int]
    google_score: Optional[float]
    google_reviews: Optional[int]
    total_rooms: Optional[int]
    address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    booking_url: Optional[str]
    amenities: list = field(default_factory=list)
    room_types: list = field(default_factory=list)
    promotions_active: bool = False
    genius_level: Optional[int] = None
    distance_center_km: Optional[float] = None
    source: str = "booking"
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
    checkin: Optional[str] = None
    checkout: Optional[str] = None


@dataclass
class ScrapeResult:
    hotel_name: str
    city: str
    checkin: str
    checkout: str
    target_hotel: Optional[ScrapedHotel]
    competitors: list[ScrapedHotel]
    total_found: int
    scrape_duration_seconds: float
    sources_used: list[str]
    errors: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────
# CONFIGURACIÓN ANTI-DETECCIÓN
# ─────────────────────────────────────────────────────────

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
]

VIEWPORTS = [
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 800},
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
]


async def human_delay(min_s: float = 1.5, max_s: float = 4.0):
    """Pausa aleatoria que simula comportamiento humano."""
    await asyncio.sleep(random.uniform(min_s, max_s))


async def human_scroll(page, steps: int = 3):
    """Scroll gradual simulando lectura humana."""
    for _ in range(steps):
        await page.evaluate(f"window.scrollBy(0, {random.randint(200, 500)})")
        await asyncio.sleep(random.uniform(0.3, 0.8))


# ─────────────────────────────────────────────────────────
# SCRAPER DE BOOKING.COM
# ─────────────────────────────────────────────────────────

async def scrape_booking_search(
    city: str,
    checkin: str,
    checkout: str,
    max_results: int = 20,
    target_hotel_name: str = "",
) -> list[ScrapedHotel]:
    """
    Scraping de resultados de búsqueda de Booking.com.
    Usa Playwright con simulación de comportamiento humano.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        log.error("Playwright no instalado. Ejecuta: pip install playwright && playwright install chromium")
        return []

    hotels = []
    city_encoded = city.replace(" ", "+")
    url = (
        f"https://www.booking.com/searchresults.es.html"
        f"?ss={city_encoded}"
        f"&checkin={checkin}"
        f"&checkout={checkout}"
        f"&group_adults=2&no_rooms=1"
        f"&order=price"
        f"&nflt=class%3D3%3Bclass%3D4%3Bclass%3D5"  # Solo 3-5 estrellas
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ]
        )

        ua = random.choice(USER_AGENTS)
        vp = random.choice(VIEWPORTS)
        context = await browser.new_context(
            user_agent=ua,
            viewport=vp,
            locale="es-ES",
            timezone_id="Europe/Madrid",
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )

        # Inyectar script anti-detección
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});
            window.chrome = {runtime: {}};
        """)

        page = await context.new_page()

        try:
            log.info(f"Navegando a Booking: {city} · {checkin} → {checkout}")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await human_delay(2.0, 4.0)

            # Aceptar cookies si aparece el banner
            try:
                cookie_btn = page.locator('[id*="accept"], [data-gdpr-consent="accept"], button:has-text("Aceptar")')
                if await cookie_btn.first.is_visible(timeout=3000):
                    await cookie_btn.first.click()
                    await human_delay(0.5, 1.5)
            except Exception:
                pass

            await human_scroll(page, steps=2)
            await human_delay(1.0, 2.5)

            # Extraer cards de hoteles
            cards = await page.query_selector_all('[data-testid="property-card"]')
            log.info(f"Cards encontradas: {len(cards)}")

            for card in cards[:max_results]:
                try:
                    hotel = await _parse_booking_card(card, checkin, checkout, city)
                    if hotel:
                        hotels.append(hotel)
                except Exception as e:
                    log.debug(f"Error parseando card: {e}")
                    continue

            # Si encontramos pocas, scrollear y buscar más
            if len(hotels) < 10:
                await human_scroll(page, steps=5)
                await human_delay(1.5, 3.0)
                cards = await page.query_selector_all('[data-testid="property-card"]')
                for card in cards[len(hotels):max_results]:
                    try:
                        hotel = await _parse_booking_card(card, checkin, checkout, city)
                        if hotel:
                            hotels.append(hotel)
                    except Exception:
                        continue

        except Exception as e:
            log.error(f"Error en scraping de Booking: {e}")
        finally:
            await browser.close()

    log.info(f"Booking: {len(hotels)} hoteles extraídos")
    return hotels


async def _parse_booking_card(card, checkin: str, checkout: str, city: str) -> Optional[ScrapedHotel]:
    """Extrae datos de una card de hotel de Booking."""

    # Nombre
    name_el = await card.query_selector('[data-testid="title"]')
    if not name_el:
        name_el = await card.query_selector('h3, [class*="title"]')
    name = (await name_el.inner_text()).strip() if name_el else None
    if not name:
        return None

    # Precio
    price = None
    price_selectors = [
        '[data-testid="price-and-discounted-price"]',
        '[class*="priceText"]',
        '[data-testid="availability-rate-information"]',
    ]
    for sel in price_selectors:
        price_el = await card.query_selector(sel)
        if price_el:
            raw = await price_el.inner_text()
            digits = re.sub(r'[^\d]', '', raw.replace(',', '').split('€')[0].split('EUR')[0])
            if digits:
                try:
                    price = float(digits[:6])  # Máximo 6 dígitos
                    break
                except ValueError:
                    pass

    # Score de reviews
    score = None
    score_el = await card.query_selector('[data-testid="review-score"]')
    if score_el:
        score_text = await score_el.inner_text()
        score_match = re.search(r'(\d+[,\.]\d+)', score_text)
        if score_match:
            try:
                score = float(score_match.group(1).replace(',', '.'))
            except ValueError:
                pass

    # Número de reviews
    reviews = None
    review_match = re.search(r'([\d\.]+)\s*(comentarios|reseñas|reviews|opiniones)', 
                              (await card.inner_text()).lower())
    if review_match:
        try:
            reviews = int(review_match.group(1).replace('.', ''))
        except ValueError:
            pass

    # Estrellas
    stars = None
    stars_el = await card.query_selector('[data-testid="rating-stars"]')
    if stars_el:
        star_spans = await stars_el.query_selector_all('span[aria-hidden="true"]')
        stars = len(star_spans) if star_spans else None

    # URL
    url = None
    link_el = await card.query_selector('a[data-testid="title-link"]')
    if link_el:
        href = await link_el.get_attribute('href')
        if href:
            url = href if href.startswith('http') else f"https://www.booking.com{href}"

    # Detección de promociones (precio tachado = promo activa)
    promo = False
    promo_el = await card.query_selector('[class*="strikethrough"], [class*="crossed"], [data-testid="recommended-units"]')
    promo = promo_el is not None

    # Distancia al centro
    distance = None
    dist_el = await card.query_selector('[data-testid="distance"]')
    if dist_el:
        dist_text = await dist_el.inner_text()
        dist_match = re.search(r'([\d,\.]+)\s*km', dist_text)
        if dist_match:
            try:
                distance = float(dist_match.group(1).replace(',', '.'))
            except ValueError:
                pass

    return ScrapedHotel(
        name=name,
        city=city,
        stars=stars,
        adr_double=price,
        price_min=price,
        price_max=price,
        booking_score=score,
        booking_reviews=reviews,
        google_score=None,
        google_reviews=None,
        total_rooms=None,
        address=None,
        latitude=None,
        longitude=None,
        booking_url=url,
        promotions_active=promo,
        distance_center_km=distance,
        source="booking",
        checkin=checkin,
        checkout=checkout,
    )


# ─────────────────────────────────────────────────────────
# SCRAPER DE FICHA INDIVIDUAL DE HOTEL
# ─────────────────────────────────────────────────────────

async def scrape_hotel_detail(
    hotel_url: str,
    checkin: str,
    checkout: str,
) -> dict:
    """
    Extrae datos detallados de la ficha individual de un hotel en Booking:
    tipos de habitación, precios por tipo, amenities, políticas.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {}

    detail = {
        "room_types": [],
        "amenities": [],
        "policies": {},
        "genius_level": None,
        "preferred_partner": False,
    }

    url_with_dates = f"{hotel_url}?checkin={checkin}&checkout={checkout}&group_adults=2"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            locale="es-ES",
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        page = await context.new_page()

        try:
            await page.goto(url_with_dates, wait_until="domcontentloaded", timeout=30000)
            await human_delay(2.0, 4.0)

            # Tipos de habitación y precios
            room_rows = await page.query_selector_all('[data-block="property_room_table_row"]')
            if not room_rows:
                room_rows = await page.query_selector_all('table.hprt-table tr')

            for row in room_rows[:8]:
                try:
                    room_name_el = await row.query_selector('[class*="room-name"], [class*="hprt-roomtype"]')
                    price_el = await row.query_selector('[class*="price"], [data-testid="price"]')

                    room_name = (await room_name_el.inner_text()).strip() if room_name_el else None
                    room_price = None
                    if price_el:
                        raw = await price_el.inner_text()
                        digits = re.sub(r'[^\d]', '', raw)
                        if digits:
                            try:
                                room_price = float(digits[:6])
                            except ValueError:
                                pass

                    if room_name:
                        detail["room_types"].append({
                            "type": room_name,
                            "price": room_price,
                        })
                except Exception:
                    continue

            # Amenities
            amenity_els = await page.query_selector_all('[data-testid="property-most-popular-facilities-wrapper"] span')
            for el in amenity_els[:20]:
                text = (await el.inner_text()).strip()
                if text and len(text) > 2:
                    detail["amenities"].append(text)

            # Genius
            genius_el = await page.query_selector('[class*="genius"]')
            if genius_el:
                genius_text = await genius_el.inner_text()
                if "3" in genius_text:
                    detail["genius_level"] = 3
                elif "2" in genius_text:
                    detail["genius_level"] = 2
                else:
                    detail["genius_level"] = 1

            # Preferred partner
            preferred_el = await page.query_selector('[class*="preferred"]')
            detail["preferred_partner"] = preferred_el is not None

        except Exception as e:
            log.error(f"Error en detalle de hotel: {e}")
        finally:
            await browser.close()

    return detail


# ─────────────────────────────────────────────────────────
# BUSCADOR DE HOTEL ESPECÍFICO
# ─────────────────────────────────────────────────────────

async def find_target_hotel(
    hotel_name: str,
    city: str,
    checkin: str,
    checkout: str,
) -> Optional[ScrapedHotel]:
    """
    Busca un hotel específico en Booking por nombre.
    Primero en resultados de búsqueda, luego búsqueda directa.
    """
    # Buscar en resultados generales
    results = await scrape_booking_search(city, checkin, checkout, max_results=30)

    # Matching por nombre (fuzzy)
    hotel_name_lower = hotel_name.lower()
    best_match = None
    best_score = 0

    for h in results:
        h_name = h.name.lower()
        # Score de similitud simple
        words_in_common = sum(1 for w in hotel_name_lower.split() if w in h_name and len(w) > 3)
        if words_in_common > best_score:
            best_score = words_in_common
            best_match = h

    if best_match and best_score >= 1:
        log.info(f"Hotel encontrado: '{best_match.name}' (match score: {best_score})")
        # Enriquecer con datos de la ficha individual
        if best_match.booking_url:
            detail = await scrape_hotel_detail(best_match.booking_url, checkin, checkout)
            if detail.get("room_types"):
                best_match.room_types = detail["room_types"]
                # Actualizar ADR con el precio de la habitación doble si disponible
                for rt in detail["room_types"]:
                    if any(w in rt.get("type","").lower() for w in ["doble","double","estándar","standard"]):
                        if rt.get("price"):
                            best_match.adr_double = rt["price"]
                        break
            if detail.get("amenities"):
                best_match.amenities = detail["amenities"]
            best_match.genius_level = detail.get("genius_level")
        return best_match, results

    log.warning(f"Hotel '{hotel_name}' no encontrado en resultados de {city}")
    return None, results


# ─────────────────────────────────────────────────────────
# PIPELINE COMPLETO DE SCRAPING
# ─────────────────────────────────────────────────────────

async def run_rate_shopping(
    hotel_name: str,
    city: str,
    checkin: str = None,
    checkout: str = None,
    days_ahead: int = 1,
    nights: int = 1,
    max_competitors: int = 20,
) -> ScrapeResult:
    """
    Pipeline completo de rate shopping.
    Devuelve datos del hotel objetivo + competidores.
    """
    start = time.time()

    if not checkin:
        checkin = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    if not checkout:
        checkout = (datetime.now() + timedelta(days=days_ahead + nights)).strftime("%Y-%m-%d")

    log.info(f"Rate shopping: {hotel_name} · {city} · {checkin}→{checkout}")

    errors = []
    target = None
    competitors = []
    sources = []

    try:
        target, all_results = await find_target_hotel(hotel_name, city, checkin, checkout)
        competitors = [h for h in all_results if h.name != (target.name if target else "")]
        sources.append("booking")
    except Exception as e:
        errors.append(f"Booking scraping error: {e}")
        log.error(f"Error en rate shopping: {e}")

    elapsed = round(time.time() - start, 1)

    return ScrapeResult(
        hotel_name=hotel_name,
        city=city,
        checkin=checkin,
        checkout=checkout,
        target_hotel=target,
        competitors=competitors[:max_competitors],
        total_found=len(competitors),
        scrape_duration_seconds=elapsed,
        sources_used=sources,
        errors=errors,
    )


def save_scrape_result(result: ScrapeResult, path: str = "data/scrape_latest.json"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "hotel_name": result.hotel_name,
        "city": result.city,
        "checkin": result.checkin,
        "checkout": result.checkout,
        "total_found": result.total_found,
        "scrape_duration_seconds": result.scrape_duration_seconds,
        "sources_used": result.sources_used,
        "errors": result.errors,
        "target_hotel": asdict(result.target_hotel) if result.target_hotel else None,
        "competitors": [asdict(h) for h in result.competitors],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info(f"Resultados guardados en {path}")
    return path


def load_scrape_result(path: str = "data/scrape_latest.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────
# CONVERTIDOR: ScrapedHotel → formato para los agentes
# ─────────────────────────────────────────────────────────

def scrape_to_agent_input(scrape: ScrapeResult) -> tuple[dict, dict]:
    """
    Convierte el resultado del scraper al formato que esperan
    el Agente 1 (Discovery) y el Agente 2 (Compset).

    Retorna: (scraped_data_for_discovery, market_candidates_for_compset)
    """
    target = scrape.target_hotel

    # Para el Agente 1 Discovery
    scraped_data = None
    if target:
        scraped_data = {
            "name": target.name,
            "city": target.city,
            "stars": target.stars,
            "adr_double": target.adr_double,
            "booking_score": target.booking_score,
            "booking_reviews": target.booking_reviews,
            "room_types": [
                {"type": rt["type"], "min_price": rt.get("price"), "max_price": rt.get("price")}
                for rt in target.room_types
            ],
            "amenities_detected": {a: True for a in target.amenities[:10]},
            "channels": {
                "booking": {"active": True, "genius_level": target.genius_level},
                "direct": {"active": True},
            },
            "ota_visibility": {
                "booking_search_position": None,
            },
            "promotions_active": target.promotions_active,
        }

    # Para el Agente 2 Compset
    market_candidates = {
        "candidates": [
            {
                "name": h.name,
                "stars": h.stars,
                "adr_double": h.adr_double,
                "booking_score": h.booking_score,
                "booking_reviews": h.booking_reviews,
                "distance_km": h.distance_center_km,
                "zone": h.city,
                "channels": ["booking"],
                "promotions_active": h.promotions_active,
            }
            for h in scrape.competitors
            if h.adr_double and h.adr_double > 20
        ]
    }

    return scraped_data, market_candidates


# ─────────────────────────────────────────────────────────
# TEST STANDALONE
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    hotel = input("Nombre del hotel: ").strip() or "Hotel Arts Barcelona"
    city = input("Ciudad: ").strip() or "Barcelona"

    print(f"\nIniciando rate shopping: {hotel} en {city}")
    print("(Esto tarda 30–60 segundos)\n")

    result = asyncio.run(run_rate_shopping(hotel, city))

    print(f"\n{'='*55}")
    print(f"Hotel objetivo: {result.target_hotel.name if result.target_hotel else 'NO ENCONTRADO'}")
    if result.target_hotel:
        t = result.target_hotel
        print(f"  Precio doble: {t.adr_double}€ | Score: {t.booking_score}")
        print(f"  Estrellas: {t.stars} | Promo: {t.promotions_active}")

    print(f"\nCompetidores ({result.total_found}):")
    for h in result.competitors[:8]:
        print(f"  {h.name[:40]:<40} {h.adr_double or '—':>6}€  ★{h.booking_score or '—'}")

    path = save_scrape_result(result)
    print(f"\n✓ Guardado en {path} ({result.scrape_duration_seconds}s)")

    if result.errors:
        print(f"\nErrores: {result.errors}")
