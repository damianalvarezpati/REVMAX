"""
RevMax — Scheduler de Alertas
================================
Corre en segundo plano cada hora.
Hace rate shopping rápido y ejecuta el motor de alertas.
Completamente independiente del informe diario.

Uso:
  python alert_scheduler.py           # arranca el loop horario
  python alert_scheduler.py --now     # ejecuta ahora mismo (test)
"""

import asyncio
import argparse
import json
import os
import sys
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import schedule
import time
import threading

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/alerts.log"),
    ]
)


async def check_and_alert(cfg: dict):
    """
    Ciclo completo de una comprobación de alertas:
    1. Scraping rápido del mercado
    2. Análisis mínimo (Discovery + Compset + Pricing + Demand)
    3. Motor de alertas con los 6 triggers
    4. Envío si hay alertas
    """
    hotel_name = cfg.get("name", "")
    city = cfg.get("city", "")
    api_key = cfg.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
    plan = cfg.get("plan", "pro")
    smtp_email = cfg.get("smtp_email", "")
    smtp_password = cfg.get("smtp_password", "")
    recipient = cfg.get("report_recipient", smtp_email)

    if not hotel_name or not api_key:
        log.warning("Falta nombre de hotel o API key — omitiendo comprobación")
        return

    log.info(f"Comprobando alertas: {hotel_name}")

    try:
        # Scraping rápido (solo precios, sin detalle de habitaciones)
        scraped_data = None
        market_candidates = None
        try:
            from scraper.rate_shopper import run_rate_shopping, scrape_to_agent_input
            scrape = await run_rate_shopping(
                hotel_name=hotel_name,
                city=city or hotel_name,
                max_competitors=15,
            )
            scraped_data, market_candidates = scrape_to_agent_input(scrape)
        except Exception as e:
            log.warning(f"Scraping falló: {e} — usando análisis IA")

        # Análisis mínimo para construir el snapshot
        from orchestrator import run_full_analysis
        result = await run_full_analysis(
            hotel_name=hotel_name,
            city_hint=city,
            api_key=api_key,
            scraped_data=scraped_data,
            market_candidates=market_candidates,
        )

        # Construir snapshot del mercado
        from agents.alert_engine import (
            build_snapshot_from_analysis,
            run_alert_engine,
            send_alert_email,
            build_alert_email_html,
        )

        snapshot = build_snapshot_from_analysis(result)
        alerts = run_alert_engine(snapshot, plan=plan)

        if not alerts:
            log.info(f"Sin alertas para {hotel_name}")
            return

        log.info(f"{len(alerts)} alerta(s) detectada(s) para {hotel_name}")
        for a in alerts:
            log.info(f"  [{a.priority.upper()}] {a.title}")

        # Guardar preview HTML
        os.makedirs("data", exist_ok=True)
        html = build_alert_email_html(alerts, hotel_name)
        with open("data/alert_latest.html", "w", encoding="utf-8") as f:
            f.write(html)

        # Enviar email si está configurado
        if smtp_email and smtp_password and recipient:
            send_alert_email(alerts, hotel_name, recipient, smtp_email, smtp_password)
            log.info(f"Email de alerta enviado a {recipient}")
        else:
            log.info("SMTP no configurado — alerta guardada en data/alert_latest.html")

        # Si hay portal activo, guardar alertas en la DB del portal
        try:
            import sqlite3
            portal_db = "data/portal.db"
            if os.path.exists(portal_db):
                conn = sqlite3.connect(portal_db)
                hotel_row = conn.execute(
                    "SELECT id FROM hotels WHERE name LIKE ?",
                    (f"%{hotel_name[:20]}%",)
                ).fetchone()
                if hotel_row:
                    for a in alerts:
                        conn.execute(
                            "INSERT INTO alerts (hotel_id, date, level, message) VALUES (?, ?, ?, ?)",
                            (hotel_row[0], datetime.now().strftime("%Y-%m-%d"),
                             a.priority, a.title)
                        )
                    conn.commit()
                conn.close()
        except Exception:
            pass

    except Exception as e:
        log.error(f"Error en comprobación de alertas: {e}")


def run_check(cfg: dict):
    """Wrapper síncrono para el scheduler."""
    asyncio.run(check_and_alert(cfg))


def main():
    parser = argparse.ArgumentParser(description="RevMax — Scheduler de alertas")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--now",    action="store_true", help="Ejecutar ahora mismo")
    parser.add_argument("--interval", type=int, default=60,
                        help="Intervalo en minutos entre comprobaciones (default: 60)")
    args = parser.parse_args()

    cfg = {}
    if os.path.exists(args.config):
        with open(args.config) as f:
            cfg = json.load(f)
    else:
        log.error(f"Config no encontrada: {args.config}")
        log.error("Ejecuta primero: python setup_wizard.py")
        sys.exit(1)

    if args.now:
        log.info("Ejecutando comprobación de alertas ahora...")
        asyncio.run(check_and_alert(cfg))
        return

    interval = args.interval
    log.info(f"RevMax Alert Scheduler iniciado")
    log.info(f"Hotel: {cfg.get('name', '?')} · Ciudad: {cfg.get('city', '?')}")
    log.info(f"Comprobación cada {interval} minutos")
    log.info(f"Plan: {cfg.get('plan', 'pro')}")
    log.info("Deja esta ventana abierta. Ctrl+C para detener.\n")

    # Primera ejecución inmediata
    run_check(cfg)

    # Programar ejecuciones periódicas
    schedule.every(interval).minutes.do(run_check, cfg)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
