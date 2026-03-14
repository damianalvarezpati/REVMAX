"""
RevMax — Scraper de precios de Booking.com
Obtiene precios de tu hotel y la competencia para una fecha dada.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import random
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

HEADERS_POOL = [
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
]


@dataclass
class HotelPrice:
    name: str
    price: Optional[float]
    currency: str
    stars: Optional[int]
    review_score: Optional[float]
    review_count: Optional[int]
    room_type: Optional[str]
    availability: bool
    url: str
    scraped_at: str
    checkin: str
    checkout: str
    platform: str = "booking"


def _get(url: str, retries: int = 3) -> Optional[requests.Response]:
    """HTTP GET con reintentos y headers rotatorios."""
    for attempt in range(retries):
        try:
            headers = random.choice(HEADERS_POOL)
            time.sleep(random.uniform(2.0, 4.5))
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                return resp
            log.warning(f"Status {resp.status_code} en intento {attempt+1}")
        except Exception as e:
            log.warning(f"Error en intento {attempt+1}: {e}")
    return None


def build_booking_url(city: str, checkin: str, checkout: str, adults: int = 2) -> str:
    """
    Construye URL de búsqueda de Booking.com.
    checkin/checkout formato: YYYY-MM-DD
    """
    city_slug = city.lower().replace(" ", "+")
    return (
        f"https://www.booking.com/searchresults.es.html"
        f"?ss={city_slug}"
        f"&checkin={checkin}"
        f"&checkout={checkout}"
        f"&group_adults={adults}"
        f"&no_rooms=1"
        f"&order=price"
    )


def parse_booking_results(html: str, checkin: str, checkout: str) -> list[HotelPrice]:
    """Parsea resultados de búsqueda de Booking.com."""
    soup = BeautifulSoup(html, "html.parser")
    hotels = []

    # Booking usa data-testid para sus cards — más estable que clases CSS
    cards = soup.find_all("div", {"data-testid": "property-card"})

    if not cards:
        # Fallback: buscar por clases comunes
        cards = soup.find_all("div", class_=lambda c: c and "sr_property_block" in c)

    log.info(f"Encontradas {len(cards)} propiedades en la página")

    for card in cards:
        try:
            # Nombre
            name_el = (
                card.find(attrs={"data-testid": "title"})
                or card.find("span", class_=lambda c: c and "fcab3ed991" in (c or ""))
                or card.find("h3")
            )
            name = name_el.get_text(strip=True) if name_el else "Desconocido"

            # Precio
            price = None
            price_el = (
                card.find(attrs={"data-testid": "price-and-discounted-price"})
                or card.find("span", class_=lambda c: c and "fcab3ed991" in (c or ""))
            )
            if price_el:
                raw = price_el.get_text(strip=True).replace("\xa0", "").replace(".", "").replace(",", ".")
                digits = "".join(c for c in raw if c.isdigit() or c == ".")
                try:
                    price = float(digits.split(".")[0]) if digits else None
                except ValueError:
                    price = None

            # Score de reviews
            score_el = card.find(attrs={"data-testid": "review-score"})
            review_score = None
            review_count = None
            if score_el:
                score_text = score_el.get_text(strip=True)
                nums = [t for t in score_text.split() if t.replace(",", ".").replace(".", "").isdigit()]
                if nums:
                    try:
                        review_score = float(nums[0].replace(",", "."))
                    except ValueError:
                        pass

            # Estrellas
            stars_el = card.find("span", {"data-testid": "rating-stars"})
            stars = None
            if stars_el:
                star_icons = stars_el.find_all("span", {"aria-hidden": "true"})
                stars = len(star_icons) if star_icons else None

            # URL
            link_el = card.find("a", {"data-testid": "title-link"}) or card.find("a", href=True)
            url = link_el["href"] if link_el and "href" in link_el.attrs else ""
            if url and not url.startswith("http"):
                url = "https://www.booking.com" + url

            hotels.append(
                HotelPrice(
                    name=name,
                    price=price,
                    currency="EUR",
                    stars=stars,
                    review_score=review_score,
                    review_count=review_count,
                    room_type=None,
                    availability=price is not None,
                    url=url,
                    scraped_at=datetime.now().isoformat(),
                    checkin=checkin,
                    checkout=checkout,
                )
            )
        except Exception as e:
            log.warning(f"Error parseando card: {e}")
            continue

    return hotels


def scrape_city_prices(
    city: str,
    checkin: Optional[str] = None,
    checkout: Optional[str] = None,
    max_hotels: int = 20,
) -> list[HotelPrice]:
    """
    Punto de entrada principal.
    Devuelve lista de hoteles con precios para la ciudad y fechas dadas.
    """
    if not checkin:
        checkin = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    if not checkout:
        checkout = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")

    log.info(f"Scraping {city} · {checkin} → {checkout}")
    url = build_booking_url(city, checkin, checkout)
    log.info(f"URL: {url}")

    resp = _get(url)
    if not resp:
        log.error("No se pudo obtener la página de Booking.com")
        return []

    hotels = parse_booking_results(resp.text, checkin, checkout)
    return hotels[:max_hotels]


def save_results(hotels: list[HotelPrice], path: str = "data/prices.json"):
    """Guarda resultados en JSON."""
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(h) for h in hotels], f, ensure_ascii=False, indent=2)
    log.info(f"Guardados {len(hotels)} hoteles en {path}")


if __name__ == "__main__":
    # Test rápido
    city = input("Ciudad a analizar (ej: Barcelona): ").strip() or "Barcelona"
    hotels = scrape_city_prices(city, max_hotels=15)

    print(f"\n{'='*60}")
    print(f"Resultados para {city}")
    print(f"{'='*60}")
    for h in hotels:
        precio = f"{h.price:.0f}€" if h.price else "N/D"
        score = f"{h.review_score}" if h.review_score else "—"
        print(f"  {h.name[:45]:<45} {precio:>6}  ★{score}")

    save_results(hotels, "data/prices_latest.json")
    print(f"\nDatos guardados en data/prices_latest.json")
