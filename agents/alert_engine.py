"""
RevMax — Módulo A: Motor de Alertas en Tiempo Real
=====================================================
Experto en sistemas de alertas para revenue management hotelero
Referencia: OTA Insight Alerts, RateGain RateAlert, Duetto GameChanger

Los 6 triggers profesionales:
  1. Market price change       — media del compset sube/baja >10%
  2. Competitor price movement — competidor individual cambia >15€
  3. Competitor sold out       — competidor sin disponibilidad = señal de demanda alta
  4. Market pickup signal      — disponibilidad cae + precios suben en el compset
  5. Event detection           — evento local detectado que afecta demanda
  6. Revenue opportunity       — tu precio >12% por debajo del mercado

REGLAS PROFESIONALES:
  - Cooldown de 6h entre alertas del mismo tipo para el mismo hotel
  - Máximo 3 alertas/día en plan Pro, sin límite agrupado en Premium
  - Cada alerta incluye: qué pasó + magnitud + precio actual + acción concreta
  - Umbral mínimo de significancia para evitar ruido
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
# MODELOS DE DATOS
# ─────────────────────────────────────────────────────────

@dataclass
class MarketSnapshot:
    """Snapshot del mercado en un momento dado. Se compara con el anterior."""
    hotel_name: str
    your_price: float
    market_avg: float
    market_min: float
    market_max: float
    compset_prices: dict          # {nombre: precio}
    compset_availability: dict    # {nombre: True/False (disponible)}
    demand_score: int             # 0-100
    events_detected: list[str]
    captured_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Alert:
    """Una alerta generada por el motor."""
    trigger_type: str             # market_price | competitor_move | sold_out | pickup | event | opportunity
    priority: str                 # high | medium | low
    title: str
    body: str
    recommendation: str           # Acción concreta con número
    your_price: float
    market_avg: float
    delta_eur: float              # Cambio en euros
    delta_pct: float              # Cambio en porcentaje
    competitor_name: Optional[str] = None
    event_name: Optional[str] = None
    hotel_name: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    sent: bool = False


# ─────────────────────────────────────────────────────────
# UMBRALES PROFESIONALES
# ─────────────────────────────────────────────────────────

THRESHOLDS = {
    # Trigger 1: cambio en media del mercado
    "market_price_change_pct":      10.0,   # % mínimo de cambio en la media
    "market_price_change_eur":       8.0,   # € mínimo de cambio absoluto

    # Trigger 2: movimiento de competidor individual
    "competitor_move_eur":          15.0,   # € mínimo de cambio en un competidor
    "competitor_move_pct":          12.0,   # % mínimo de cambio en un competidor

    # Trigger 3: competidor agotado
    # (binario — disponible/no disponible, siempre relevante)

    # Trigger 4: señal de pickup
    "pickup_availability_drop_pct": 20.0,   # % de caída de disponibilidad del compset
    "pickup_price_increase_count":   2,     # nº de competidores que han subido precio

    # Trigger 5: evento detectado
    # (cualquier evento nuevo con impacto alto genera alerta)

    # Trigger 6: oportunidad de revenue
    "opportunity_below_market_pct": 12.0,   # % por debajo de la media para generar alerta
    "opportunity_min_eur":          15.0,   # € mínimo de diferencia para generar alerta

    # Cooldown entre alertas del mismo tipo
    "cooldown_hours":                6,

    # Límite diario por plan
    "daily_limit_basic":             1,
    "daily_limit_pro":               3,
    "daily_limit_premium":          99,
}


# ─────────────────────────────────────────────────────────
# BASE DE DATOS DE SNAPSHOTS Y ALERTAS
# ─────────────────────────────────────────────────────────

def get_alert_db(db_path: str = "data/alerts.db") -> sqlite3.Connection:
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_name  TEXT NOT NULL,
            data        TEXT NOT NULL,
            captured_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS alerts_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_name      TEXT NOT NULL,
            trigger_type    TEXT NOT NULL,
            priority        TEXT NOT NULL,
            title           TEXT NOT NULL,
            body            TEXT,
            recommendation  TEXT,
            your_price      REAL,
            market_avg      REAL,
            delta_eur       REAL,
            delta_pct       REAL,
            competitor_name TEXT,
            event_name      TEXT,
            sent            INTEGER DEFAULT 0,
            created_at      TEXT NOT NULL
        );
    """)
    conn.commit()
    return conn


def save_snapshot(snapshot: MarketSnapshot, db_path: str = "data/alerts.db"):
    conn = get_alert_db(db_path)
    conn.execute(
        "INSERT INTO snapshots (hotel_name, data, captured_at) VALUES (?, ?, ?)",
        (snapshot.hotel_name, json.dumps(asdict(snapshot)), snapshot.captured_at)
    )
    conn.commit()
    conn.close()


def get_last_snapshot(hotel_name: str, db_path: str = "data/alerts.db") -> Optional[MarketSnapshot]:
    conn = get_alert_db(db_path)
    row = conn.execute(
        "SELECT data FROM snapshots WHERE hotel_name = ? ORDER BY captured_at DESC LIMIT 1 OFFSET 1",
        (hotel_name,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    data = json.loads(row["data"])
    return MarketSnapshot(**data)


def save_alert(alert: Alert, db_path: str = "data/alerts.db"):
    conn = get_alert_db(db_path)
    conn.execute("""
        INSERT INTO alerts_log
        (hotel_name, trigger_type, priority, title, body, recommendation,
         your_price, market_avg, delta_eur, delta_pct, competitor_name, event_name, sent, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        alert.hotel_name, alert.trigger_type, alert.priority,
        alert.title, alert.body, alert.recommendation,
        alert.your_price, alert.market_avg, alert.delta_eur, alert.delta_pct,
        alert.competitor_name, alert.event_name,
        1 if alert.sent else 0, alert.created_at
    ))
    conn.commit()
    conn.close()


def check_cooldown(hotel_name: str, trigger_type: str, db_path: str = "data/alerts.db") -> bool:
    """Devuelve True si está en cooldown (no debe enviarse otra alerta del mismo tipo)."""
    cooldown_h = THRESHOLDS["cooldown_hours"]
    cutoff = (datetime.now() - timedelta(hours=cooldown_h)).isoformat()
    conn = get_alert_db(db_path)
    count = conn.execute(
        """SELECT COUNT(*) as n FROM alerts_log
           WHERE hotel_name = ? AND trigger_type = ? AND created_at > ?""",
        (hotel_name, trigger_type, cutoff)
    ).fetchone()["n"]
    conn.close()
    return count > 0


def count_today_alerts(hotel_name: str, db_path: str = "data/alerts.db") -> int:
    """Cuántas alertas se han enviado hoy para este hotel."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_alert_db(db_path)
    n = conn.execute(
        "SELECT COUNT(*) as n FROM alerts_log WHERE hotel_name = ? AND created_at LIKE ?",
        (hotel_name, f"{today}%")
    ).fetchone()["n"]
    conn.close()
    return n


# ─────────────────────────────────────────────────────────
# LOS 6 TRIGGERS PROFESIONALES
# ─────────────────────────────────────────────────────────

def _trigger_market_price_change(current: MarketSnapshot, previous: MarketSnapshot) -> Optional[Alert]:
    """
    Trigger 1: La media del mercado ha subido o bajado significativamente.
    Umbral: >10% o >8€ de cambio en la media del compset.
    """
    if not previous or previous.market_avg == 0:
        return None

    delta_eur = current.market_avg - previous.market_avg
    delta_pct = (delta_eur / previous.market_avg) * 100

    if abs(delta_pct) < THRESHOLDS["market_price_change_pct"] and \
       abs(delta_eur) < THRESHOLDS["market_price_change_eur"]:
        return None

    direction = "subido" if delta_eur > 0 else "bajado"
    icon = "↑" if delta_eur > 0 else "↓"
    priority = "high" if abs(delta_pct) > 15 else "medium"

    # Calcular precio recomendado
    gap = current.market_avg - current.your_price
    if delta_eur > 0 and current.your_price < current.market_avg:
        rec_price = round(current.your_price + (gap * 0.6), 0)
        rec = f"Sube tu precio de {current.your_price:.0f}€ a {rec_price:.0f}€"
    elif delta_eur < 0 and current.your_price > current.market_avg:
        rec_price = round(current.market_avg * 0.98, 0)
        rec = f"Considera bajar a {rec_price:.0f}€ para mantener competitividad"
    else:
        rec = f"Monitoriza — tu precio está {'bien posicionado' if gap < 10 else 'desalineado'}"

    return Alert(
        trigger_type="market_price_change",
        priority=priority,
        title=f"Media del mercado ha {direction} {icon}{abs(delta_eur):.0f}€",
        body=(
            f"La media del compset ha pasado de {previous.market_avg:.0f}€ "
            f"a {current.market_avg:.0f}€ ({delta_pct:+.1f}%).\n"
            f"Tu precio actual: {current.your_price:.0f}€ — "
            f"{'por debajo' if current.your_price < current.market_avg else 'por encima'} "
            f"del mercado en {abs(current.market_avg - current.your_price):.0f}€."
        ),
        recommendation=rec,
        your_price=current.your_price,
        market_avg=current.market_avg,
        delta_eur=round(delta_eur, 2),
        delta_pct=round(delta_pct, 1),
        hotel_name=current.hotel_name,
    )


def _trigger_competitor_move(current: MarketSnapshot, previous: MarketSnapshot) -> list[Alert]:
    """
    Trigger 2: Un competidor ha subido o bajado el precio significativamente.
    Umbral: >15€ o >12% de cambio en un competidor individual.
    """
    alerts = []
    if not previous:
        return alerts

    for comp_name, curr_price in current.compset_prices.items():
        prev_price = previous.compset_prices.get(comp_name)
        if not prev_price or not curr_price:
            continue

        delta_eur = curr_price - prev_price
        delta_pct = (delta_eur / prev_price) * 100

        if abs(delta_eur) < THRESHOLDS["competitor_move_eur"] and \
           abs(delta_pct) < THRESHOLDS["competitor_move_pct"]:
            continue

        direction = "subido" if delta_eur > 0 else "bajado"
        priority = "high" if abs(delta_eur) > 25 or abs(delta_pct) > 20 else "medium"

        if delta_eur > 0:
            if current.your_price < curr_price:
                rec = f"Tienes margen. Sube a {min(curr_price - 5, round(current.your_price * 1.10)):.0f}€"
            else:
                rec = "Tu precio ya está por encima. Monitoriza su ocupación."
        else:
            if current.your_price > curr_price:
                rec = f"Están más baratos que tú. Evalúa bajar a {curr_price + 3:.0f}€ o lanzar valor añadido."
            else:
                rec = "Están por debajo del mercado. Posible promo temporal — no reacciones aún."

        alerts.append(Alert(
            trigger_type="competitor_move",
            priority=priority,
            title=f"{comp_name[:30]} ha {direction} el precio {'+' if delta_eur > 0 else ''}{delta_eur:.0f}€",
            body=(
                f"{comp_name} ha pasado de {prev_price:.0f}€ a {curr_price:.0f}€ "
                f"({delta_pct:+.1f}%).\n"
                f"Tu precio: {current.your_price:.0f}€ · Media mercado: {current.market_avg:.0f}€."
            ),
            recommendation=rec,
            your_price=current.your_price,
            market_avg=current.market_avg,
            delta_eur=round(delta_eur, 2),
            delta_pct=round(delta_pct, 1),
            competitor_name=comp_name,
            hotel_name=current.hotel_name,
        ))

    return alerts


def _trigger_competitor_sold_out(current: MarketSnapshot, previous: MarketSnapshot) -> list[Alert]:
    """
    Trigger 3: Un competidor se ha quedado sin disponibilidad.
    Señal directa de demanda alta en el mercado.
    """
    alerts = []
    if not previous:
        return alerts

    for comp_name, is_available in current.compset_availability.items():
        was_available = previous.compset_availability.get(comp_name, True)

        # Solo alerta cuando PASA de disponible a no disponible
        if was_available and not is_available:
            comp_price = current.compset_prices.get(comp_name, 0)

            # Cuántos competidores están llenos ahora
            sold_out_count = sum(1 for v in current.compset_availability.values() if not v)
            total = len(current.compset_availability)
            sold_out_pct = (sold_out_count / total * 100) if total else 0

            priority = "high" if sold_out_pct > 30 else "medium"

            rec_price = round(current.your_price * 1.10, 0)
            rec = (
                f"Demanda alta detectada. Sube precio a {rec_price:.0f}€ "
                f"({sold_out_count}/{total} competidores sin disponibilidad)."
            )

            alerts.append(Alert(
                trigger_type="sold_out",
                priority=priority,
                title=f"{comp_name[:30]} sin disponibilidad — demanda activa",
                body=(
                    f"{comp_name} ya no tiene disponibilidad para estas fechas.\n"
                    f"{sold_out_count} de {total} competidores están llenos ({sold_out_pct:.0f}%).\n"
                    f"Tu precio actual: {current.your_price:.0f}€ · Mercado: {current.market_avg:.0f}€."
                ),
                recommendation=rec,
                your_price=current.your_price,
                market_avg=current.market_avg,
                delta_eur=0,
                delta_pct=0,
                competitor_name=comp_name,
                hotel_name=current.hotel_name,
            ))

    return alerts


def _trigger_market_pickup(current: MarketSnapshot, previous: MarketSnapshot) -> Optional[Alert]:
    """
    Trigger 4: Señal de pickup — disponibilidad cae + precios suben en el compset.
    La combinación de ambas señales indica demanda creciente real.
    """
    if not previous:
        return None

    # Calcular caída de disponibilidad
    prev_available = sum(1 for v in previous.compset_availability.values() if v)
    curr_available = sum(1 for v in current.compset_availability.values() if v)
    total = len(current.compset_availability) or 1

    availability_drop_pct = ((prev_available - curr_available) / total) * 100

    # Calcular cuántos competidores han subido precio
    price_increases = 0
    for comp, curr_price in current.compset_prices.items():
        prev_price = previous.compset_prices.get(comp, 0)
        if prev_price and curr_price > prev_price * 1.03:  # +3% mínimo
            price_increases += 1

    if availability_drop_pct < THRESHOLDS["pickup_availability_drop_pct"] or \
       price_increases < THRESHOLDS["pickup_price_increase_count"]:
        return None

    rec_price = round(current.your_price * 1.08, 0)

    return Alert(
        trigger_type="pickup_signal",
        priority="high",
        title=f"Señal de pickup — mercado acelerando",
        body=(
            f"Disponibilidad del compset ha caído un {availability_drop_pct:.0f}% "
            f"y {price_increases} competidores han subido precios.\n"
            f"La demanda está creciendo ahora mismo.\n"
            f"Tu precio: {current.your_price:.0f}€ · Mercado: {current.market_avg:.0f}€."
        ),
        recommendation=(
            f"Actúa ahora. Sube precio de {current.your_price:.0f}€ a {rec_price:.0f}€. "
            f"El mercado está absorbiendo subidas."
        ),
        your_price=current.your_price,
        market_avg=current.market_avg,
        delta_eur=round(current.market_avg - current.your_price, 2),
        delta_pct=round((current.market_avg - current.your_price) / current.your_price * 100, 1),
        hotel_name=current.hotel_name,
    )


def _trigger_event_detection(current: MarketSnapshot, previous: Optional[MarketSnapshot]) -> list[Alert]:
    """
    Trigger 5: Evento nuevo detectado que impacta demanda.
    Solo genera alerta para eventos que no estaban en el snapshot anterior.
    """
    alerts = []
    prev_events = set(previous.events_detected) if previous else set()
    new_events = [e for e in current.events_detected if e not in prev_events]

    for event in new_events:
        # Estimar impacto del evento en el precio
        event_lower = event.lower()
        if any(w in event_lower for w in ["congreso", "conferencia", "congress", "mobile world", "fitur", "mwc"]):
            impact_pct = 20
            priority = "high"
        elif any(w in event_lower for w in ["festival", "feria", "concierto", "concert", "partido", "champions"]):
            impact_pct = 15
            priority = "high"
        else:
            impact_pct = 8
            priority = "medium"

        rec_price = round(current.your_price * (1 + impact_pct / 100), 0)

        alerts.append(Alert(
            trigger_type="event_detected",
            priority=priority,
            title=f"Evento detectado: {event[:40]}",
            body=(
                f"Se ha detectado un evento próximo: {event}.\n"
                f"Impacto estimado en demanda: +{impact_pct}%.\n"
                f"Tu precio actual: {current.your_price:.0f}€ · Mercado: {current.market_avg:.0f}€."
            ),
            recommendation=(
                f"Sube precio a {rec_price:.0f}€ para las fechas del evento "
                f"(+{impact_pct}% estimado). Revisa disponibilidad del compset."
            ),
            your_price=current.your_price,
            market_avg=current.market_avg,
            delta_eur=0,
            delta_pct=float(impact_pct),
            event_name=event,
            hotel_name=current.hotel_name,
        ))

    return alerts


def _trigger_revenue_opportunity(current: MarketSnapshot) -> Optional[Alert]:
    """
    Trigger 6: Tu precio está significativamente por debajo del mercado.
    Cuantifica el dinero que se está dejando en la mesa.
    """
    if current.market_avg == 0:
        return None

    gap_pct = ((current.market_avg - current.your_price) / current.market_avg) * 100
    gap_eur = current.market_avg - current.your_price

    if gap_pct < THRESHOLDS["opportunity_below_market_pct"] or \
       gap_eur < THRESHOLDS["opportunity_min_eur"]:
        return None

    # Calcular impacto económico estimado (asumiendo 30 habitaciones, 70% ocupación)
    rooms_estimate = 30
    occupancy_estimate = 0.70
    nightly_missed = gap_eur * rooms_estimate * occupancy_estimate
    weekly_missed = nightly_missed * 7

    rec_price = round(current.market_avg * 0.96, 0)  # 4% por debajo del mercado (posición competitiva)

    return Alert(
        trigger_type="revenue_opportunity",
        priority="high",
        title=f"Oportunidad de revenue: {gap_eur:.0f}€ por debajo del mercado",
        body=(
            f"Tu precio: {current.your_price:.0f}€\n"
            f"Media del mercado: {current.market_avg:.0f}€\n"
            f"Diferencia: {gap_eur:.0f}€ ({gap_pct:.1f}% por debajo)\n\n"
            f"Impacto estimado si no se corrige:\n"
            f"~{nightly_missed:.0f}€/noche · ~{weekly_missed:.0f}€/semana en revenue potencial no capturado."
        ),
        recommendation=(
            f"Sube precio de {current.your_price:.0f}€ a {rec_price:.0f}€ "
            f"(rango sugerido: {rec_price - 5:.0f}€ – {rec_price + 10:.0f}€). "
            f"Sigues siendo competitivo y capturas el revenue que estás dejando."
        ),
        your_price=current.your_price,
        market_avg=current.market_avg,
        delta_eur=round(-gap_eur, 2),
        delta_pct=round(-gap_pct, 1),
        hotel_name=current.hotel_name,
    )


# ─────────────────────────────────────────────────────────
# MOTOR PRINCIPAL
# ─────────────────────────────────────────────────────────

def run_alert_engine(
    current: MarketSnapshot,
    plan: str = "pro",
    db_path: str = "data/alerts.db",
) -> list[Alert]:
    """
    Ejecuta los 6 triggers y devuelve las alertas que deben enviarse.
    Aplica cooldowns, límites diarios y deduplicación.
    """
    save_snapshot(current, db_path)
    previous = get_last_snapshot(current.hotel_name, db_path)

    # Límite diario según plan
    daily_limits = {
        "basic":   THRESHOLDS["daily_limit_basic"],
        "pro":     THRESHOLDS["daily_limit_pro"],
        "premium": THRESHOLDS["daily_limit_premium"],
    }
    daily_limit = daily_limits.get(plan, 3)
    today_count = count_today_alerts(current.hotel_name, db_path)

    if today_count >= daily_limit:
        log.info(f"Límite diario alcanzado ({today_count}/{daily_limit}) para {current.hotel_name}")
        return []

    # Generar candidatos de alerta
    candidates: list[Alert] = []

    # Trigger 1 — Market price change
    alert = _trigger_market_price_change(current, previous)
    if alert:
        candidates.append(alert)

    # Trigger 2 — Competitor moves
    candidates.extend(_trigger_competitor_move(current, previous))

    # Trigger 3 — Sold out
    candidates.extend(_trigger_competitor_sold_out(current, previous))

    # Trigger 4 — Pickup signal
    alert = _trigger_market_pickup(current, previous)
    if alert:
        candidates.append(alert)

    # Trigger 5 — Events
    candidates.extend(_trigger_event_detection(current, previous))

    # Trigger 6 — Revenue opportunity
    alert = _trigger_revenue_opportunity(current)
    if alert:
        candidates.append(alert)

    # Filtrar por cooldown
    to_send = []
    for alert in candidates:
        if check_cooldown(current.hotel_name, alert.trigger_type, db_path):
            log.info(f"Cooldown activo para trigger '{alert.trigger_type}' — omitida")
            continue
        to_send.append(alert)

    # Ordenar por prioridad (high primero)
    priority_order = {"high": 0, "medium": 1, "low": 2}
    to_send.sort(key=lambda a: priority_order.get(a.priority, 1))

    # Aplicar límite diario
    remaining = daily_limit - today_count
    to_send = to_send[:remaining]

    # Guardar en DB
    for alert in to_send:
        save_alert(alert, db_path)
        log.info(f"Alerta generada [{alert.priority.upper()}] {alert.title}")

    return to_send


# ─────────────────────────────────────────────────────────
# EMAIL DE ALERTA
# ─────────────────────────────────────────────────────────

PRIORITY_STYLES = {
    "high":   {"bg": "#FAECE7", "border": "#D85A30", "dot": "#D85A30", "label": "Urgente"},
    "medium": {"bg": "#FAEEDA", "border": "#BA7517", "dot": "#BA7517", "label": "Importante"},
    "low":    {"bg": "#EAF3DE", "border": "#1D9E75", "dot": "#1D9E75", "label": "Informativo"},
}


def build_alert_email_html(alerts: list[Alert], hotel_name: str) -> str:
    """Construye el HTML del email de alerta — formato corto y accionable."""

    alerts_html = ""
    for alert in alerts:
        style = PRIORITY_STYLES.get(alert.priority, PRIORITY_STYLES["medium"])
        body_lines = alert.body.replace("\n\n", "<br><br>").replace("\n", "<br>")

        alerts_html += f"""
        <div style="margin-bottom:16px;border-left:3px solid {style['border']};
                    background:{style['bg']};border-radius:0 8px 8px 0;padding:14px 16px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span style="width:8px;height:8px;border-radius:50%;
                         background:{style['dot']};display:inline-block;"></span>
            <span style="font-size:11px;font-weight:700;color:{style['border']};
                         text-transform:uppercase;letter-spacing:0.06em;">{style['label']}</span>
          </div>
          <div style="font-size:15px;font-weight:600;color:#1D2B1D;margin-bottom:8px;">
            {alert.title}
          </div>
          <div style="font-size:13px;color:#5F5E5A;line-height:1.7;margin-bottom:12px;">
            {body_lines}
          </div>
          <div style="background:rgba(255,255,255,0.7);border-radius:6px;
                      padding:10px 12px;font-size:13px;font-weight:500;color:#1D2B1D;">
            Recomendación → {alert.recommendation}
          </div>
        </div>"""

    now_str = datetime.now().strftime("%H:%M · %d de %B")
    count = len(alerts)
    plural = "alerta" if count == 1 else "alertas"

    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8">
<title>RevMax Alerta — {hotel_name}</title></head>
<body style="margin:0;padding:0;background:#F0EDE6;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">

<div style="max-width:580px;margin:20px auto;background:#fff;
            border-radius:14px;overflow:hidden;border:1px solid #DDD9D0;">

  <div style="background:#1D2B1D;padding:20px 28px 18px;">
    <div style="font-size:10px;color:#5DCAA5;font-weight:700;
                letter-spacing:0.12em;text-transform:uppercase;margin-bottom:4px;">
      RevMax · Alerta de mercado
    </div>
    <div style="font-size:19px;font-weight:700;color:#fff;">{hotel_name}</div>
    <div style="font-size:12px;color:#9FE1CB;margin-top:2px;">
      {count} {plural} detectada{'s' if count > 1 else ''} · {now_str}
    </div>
  </div>

  <div style="padding:20px 28px;">
    {alerts_html}
  </div>

  <div style="background:#F5F2EB;border-top:1px solid #DDD9D0;
              padding:12px 28px;text-align:center;">
    <p style="margin:0;font-size:11px;color:#9B9890;">
      RevMax · Alertas automáticas · Para ajustar umbrales responde a este email
    </p>
  </div>

</div>
</body></html>"""


def send_alert_email(
    alerts: list[Alert],
    hotel_name: str,
    to_email: str,
    from_email: str,
    smtp_password: str,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
):
    if not alerts:
        return

    html = build_alert_email_html(alerts, hotel_name)
    priorities = [a.priority for a in alerts]
    subject_prefix = "🔴 URGENTE" if "high" in priorities else "🟡 Alerta"
    titles = " · ".join(a.title[:35] for a in alerts[:2])
    subject = f"{subject_prefix} RevMax · {hotel_name} · {titles}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"RevMax Alerts <{from_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(smtp_host, smtp_port) as s:
        s.ehlo()
        s.starttls()
        s.login(from_email, smtp_password)
        s.sendmail(from_email, to_email, msg.as_string())

    log.info(f"Email de alerta enviado a {to_email} ({len(alerts)} alertas)")


# ─────────────────────────────────────────────────────────
# INTEGRACIÓN CON EL PIPELINE PRINCIPAL
# ─────────────────────────────────────────────────────────

def build_snapshot_from_analysis(full_analysis: dict) -> MarketSnapshot:
    """
    Convierte el output del orquestador en un MarketSnapshot
    para el motor de alertas.
    """
    outputs = full_analysis.get("agent_outputs", {})
    discovery = outputs.get("discovery", {})
    compset_data = outputs.get("compset", {})
    pricing = outputs.get("pricing", {})
    demand = outputs.get("demand", {})

    your_price = discovery.get("adr_double", 0) or 0
    market_ctx = pricing.get("market_context", {})
    market_avg = market_ctx.get("your_position_rank", 0)

    # Extraer precios y disponibilidad del compset
    primary = compset_data.get("compset", {}).get("primary", [])
    compset_prices = {}
    compset_availability = {}
    for h in primary:
        name = h.get("name", "?")
        price = h.get("last_price_checked") or h.get("adr_double")
        compset_prices[name] = price or 0
        compset_availability[name] = not h.get("promotions_active", False)

    market_avg_real = compset_data.get("compset_summary", {}).get("primary_avg_adr", 0) or 0

    return MarketSnapshot(
        hotel_name=full_analysis.get("hotel_name", "?"),
        your_price=your_price,
        market_avg=market_avg_real,
        market_min=compset_data.get("compset_summary", {}).get("primary_min_adr", 0) or 0,
        market_max=compset_data.get("compset_summary", {}).get("primary_max_adr", 0) or 0,
        compset_prices=compset_prices,
        compset_availability=compset_availability,
        demand_score=demand.get("demand_index", {}).get("score", 50) or 50,
        events_detected=demand.get("events_detected", []),
    )


# ─────────────────────────────────────────────────────────
# TEST STANDALONE
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("RevMax — Test del motor de alertas\n")

    # Snapshot anterior (hace 6 horas)
    snapshot_prev = MarketSnapshot(
        hotel_name="Hotel Casa Fuster",
        your_price=320.0,
        market_avg=310.0,
        market_min=220.0,
        market_max=480.0,
        compset_prices={
            "Hotel Majestic": 340.0,
            "Hotel Omm": 285.0,
            "Catalonia Eixample": 195.0,
            "Hotel Granados 83": 210.0,
        },
        compset_availability={
            "Hotel Majestic": True,
            "Hotel Omm": True,
            "Catalonia Eixample": True,
            "Hotel Granados 83": True,
        },
        demand_score=55,
        events_detected=[],
    )

    # Snapshot actual (situación cambiada)
    snapshot_curr = MarketSnapshot(
        hotel_name="Hotel Casa Fuster",
        your_price=320.0,          # Tu precio NO ha cambiado
        market_avg=358.0,          # Mercado SUBIÓ +15%
        market_min=245.0,
        market_max=520.0,
        compset_prices={
            "Hotel Majestic": 395.0,   # +55€ → trigger 2
            "Hotel Omm": 310.0,        # +25€ → trigger 2
            "Catalonia Eixample": 195.0,
            "Hotel Granados 83": 240.0,
        },
        compset_availability={
            "Hotel Majestic": False,   # SE HA LLENADO → trigger 3
            "Hotel Omm": True,
            "Catalonia Eixample": True,
            "Hotel Granados 83": True,
        },
        demand_score=81,
        events_detected=["Mobile World Congress 2025"],  # NUEVO → trigger 5
    )

    # Forzar guardado del snapshot previo
    db = "data/test_alerts.db"
    save_snapshot(snapshot_prev, db)
    # Simular que fue hace más de 6h (para que no esté en cooldown)
    conn = sqlite3.connect(db)
    conn.execute(
        "UPDATE snapshots SET captured_at = ? WHERE hotel_name = ?",
        ((datetime.now() - timedelta(hours=8)).isoformat(), "Hotel Casa Fuster")
    )
    conn.commit()
    conn.close()

    alerts = run_alert_engine(snapshot_curr, plan="premium", db_path=db)

    print(f"{'='*55}")
    print(f"  Alertas generadas: {len(alerts)}")
    print(f"{'='*55}\n")

    for i, alert in enumerate(alerts, 1):
        priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        icon = priority_icons.get(alert.priority, "⚪")
        print(f"{icon} Alerta {i}: [{alert.trigger_type}]")
        print(f"   Título: {alert.title}")
        print(f"   {alert.body[:120].replace(chr(10), ' ')}")
        print(f"   → {alert.recommendation}")
        print()

    # Generar preview del email
    if alerts:
        html = build_alert_email_html(alerts, "Hotel Casa Fuster")
        os.makedirs("data", exist_ok=True)
        with open("data/alert_preview.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("✓ Preview del email guardado en data/alert_preview.html")
