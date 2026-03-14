#!/usr/bin/env python3
"""
RevMax — Pipeline completo
  1. Scraper real de Booking (rate shopping)
  2. 7 agentes especializados en paralelo
  3. Email HTML ejecutivo

Uso:
  python run_revmax.py                           # usa config.json
  python run_revmax.py --hotel "Hotel Arts"      # hotel específico
  python run_revmax.py --preview                 # sin envío de email
  python run_revmax.py --no-scrape               # usa datos previos
"""

import asyncio, argparse, json, os, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def main():
    parser = argparse.ArgumentParser(description="RevMax — Director de Revenue Virtual")
    parser.add_argument("--hotel",     default="", help="Nombre del hotel")
    parser.add_argument("--city",      default="", help="Ciudad")
    parser.add_argument("--config",    default="config.json")
    parser.add_argument("--preview",   action="store_true", help="No enviar email")
    parser.add_argument("--no-scrape", action="store_true", help="Usar datos ya scrapeados")
    args = parser.parse_args()

    # ── Config ─────────────────────────────────────────────
    cfg = {}
    if os.path.exists(args.config):
        with open(args.config) as f:
            cfg = json.load(f)

    api_key = os.environ.get("ANTHROPIC_API_KEY") or cfg.get("anthropic_api_key", "")
    if not api_key:
        print("ERROR: Falta ANTHROPIC_API_KEY")
        print("       Añádela en config.json o: export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    hotel = args.hotel or cfg.get("name") or input("Nombre del hotel: ").strip()
    city  = args.city  or cfg.get("city", "")

    # ── Paso 1: Scraping ────────────────────────────────────
    scraped_data     = None
    market_candidates = None

    scrape_path = "data/scrape_latest.json"

    if args.no_scrape and os.path.exists(scrape_path):
        print("Usando datos de scraping previos (--no-scrape)")
        from scraper.rate_shopper import load_scrape_result, scrape_to_agent_input, ScrapeResult, ScrapedHotel
        raw = load_scrape_result(scrape_path)
        # Reconstruir objeto mínimo
        class _SR:
            target_hotel = None
            competitors = []
        sr = _SR()
        if raw.get("target_hotel"):
            t = raw["target_hotel"]
            sr.target_hotel = ScrapedHotel(**{k: v for k, v in t.items()
                                               if k in ScrapedHotel.__dataclass_fields__})
        sr.competitors = [
            ScrapedHotel(**{k: v for k, v in c.items()
                            if k in ScrapedHotel.__dataclass_fields__})
            for c in raw.get("competitors", [])
        ]
        scraped_data, market_candidates = scrape_to_agent_input(sr)

    else:
        print(f"\n{'─'*50}")
        print(f"Paso 1/3 — Rate shopping en tiempo real")
        print(f"Hotel: {hotel}  ·  Ciudad: {city or 'auto-detectar'}")
        print("(30–60 segundos)\n")

        try:
            from scraper.rate_shopper import run_rate_shopping, save_scrape_result, scrape_to_agent_input
            scrape_result = await run_rate_shopping(
                hotel_name=hotel,
                city=city or hotel,  # Fallback: usar nombre del hotel como ciudad hint
                max_competitors=25,
            )
            save_scrape_result(scrape_result, scrape_path)
            scraped_data, market_candidates = scrape_to_agent_input(scrape_result)

            if scrape_result.target_hotel:
                t = scrape_result.target_hotel
                print(f"✓ Hotel encontrado: {t.name}")
                print(f"  Precio: {t.adr_double}€ | Score: {t.booking_score} | ★{t.stars}")
            else:
                print(f"⚠ Hotel no encontrado en Booking — los agentes usarán estimaciones")

            print(f"✓ {scrape_result.total_found} competidores encontrados")

        except Exception as e:
            print(f"⚠ Error en scraping ({e}) — continuando con estimaciones IA")

    # ── Paso 2: Pipeline de 7 agentes ──────────────────────
    print(f"\n{'─'*50}")
    print("Paso 2/3 — Análisis con 7 agentes especializados\n")

    from orchestrator import run_full_analysis
    result = await run_full_analysis(
        hotel_name=hotel,
        city_hint=city,
        api_key=api_key,
        scraped_data=scraped_data,
        market_candidates=market_candidates,
    )
    report = result.get("report", {})

    # ── Paso 3: Email ───────────────────────────────────────
    print(f"\n{'─'*50}")
    print("Paso 3/3 — Generando informe HTML\n")

    try:
        from mailer.report_mailer_v2 import build_email_html_v2, send_email
        html = build_email_html_v2(result, report)

        os.makedirs("data", exist_ok=True)
        preview_path = "data/report_preview.html"
        with open(preview_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✓ Preview guardado: {preview_path}")
        print("  → Ábrelo en tu navegador para ver el email")

        # Enviar si está configurado
        if not args.preview:
            smtp_email    = cfg.get("smtp_email", "")
            smtp_password = cfg.get("smtp_password", "")
            recipient     = cfg.get("report_recipient", smtp_email)

            if smtp_email and smtp_password:
                send_email(
                    html,
                    subject=report.get("email_subject", f"RevMax · {hotel} · {datetime.now().strftime('%d %b')}"),
                    to_email=recipient,
                    from_email=smtp_email,
                    smtp_password=smtp_password,
                )
                print(f"✓ Email enviado a {recipient}")
            else:
                print("ℹ SMTP no configurado — solo preview")

    except Exception as e:
        print(f"✗ Error generando email: {e}")

    # ── Resumen en terminal ─────────────────────────────────
    briefing = result.get("briefing", {})
    print(f"\n{'='*50}")
    print(f"RESULTADO FINAL — {hotel}")
    print(f"{'='*50}")
    print(f"Estado  : {report.get('overall_status','?').upper()}")
    print(f"Asunto  : {report.get('email_subject','?')}")
    print(f"Confidence: {briefing.get('system_confidence','?')}")
    print(f"Tiempo  : {result.get('elapsed_seconds','?')}s")

    print("\nACCIONES PRIORITARIAS:")
    icons = {"immediate": "🔴", "this_week": "🟡", "this_month": "🟢"}
    for a in report.get("priority_actions", []):
        icon = icons.get(a.get("urgency", "this_week"), "⚪")
        print(f"\n  {icon} {a.get('rank')}. {a.get('action','')}")
        if a.get("reason"):
            print(f"     Motivo  : {a['reason']}")
        if a.get("expected_impact"):
            print(f"     Impacto : {a['expected_impact']}")

    if report.get("weekly_watchlist"):
        print(f"\n📌 ESTA SEMANA: {report['weekly_watchlist']}")

    conflicts = briefing.get("conflicts", [])
    if conflicts:
        print(f"\n⚠ {len(conflicts)} conflicto(s) de señales detectado(s)")
        for c in conflicts:
            print(f"  [{c.get('severity','?').upper()}] {c.get('description','?')}")

    print(f"\n{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())
