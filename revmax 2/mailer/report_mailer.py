"""
RevMax — Generador y enviador del informe diario
Usa Claude para escribir el informe en lenguaje natural y lo manda por email.
"""

import os
import json
import smtplib
import anthropic
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from dataclasses import asdict
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analyzer.market_analyzer import DailyAnalysis, CompetitorInsight, PriceRecommendation


# ──────────────────────────────────────────────
# 1. Generación del texto con Claude
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """Eres RevMax, el director de revenue virtual de hoteles.
Tu trabajo es analizar datos del mercado hotelero y escribir un informe diario
claro, útil y accionable para el director del hotel.

Estilo:
- Profesional pero directo, sin tecnicismos innecesarios
- Usa números concretos siempre que puedas
- Las recomendaciones deben ser específicas ("sube la suite junior a 145€ este fin de semana")
- Señala oportunidades y amenazas con claridad
- Máximo 400 palabras en el cuerpo del informe
- Escribe en español"""


def build_analysis_prompt(analysis: DailyAnalysis) -> str:
    """Convierte el análisis estructurado en un prompt para Claude."""

    comps_summary = "\n".join([
        f"  - {c.name}: {c.price}€ {'[PROMO ACTIVA]' if c.is_promotion else ''} "
        f"(score: {c.review_score or 'N/D'})"
        for c in analysis.competitors[:6]
    ])

    recs_summary = "\n".join([
        f"  - {r.room_type}: actualmente {r.current_price}€ → recomendado {r.recommended_price}€ "
        f"({r.change_pct:+.1f}%) — {r.reason}"
        for r in analysis.recommendations
    ])

    promos = ", ".join(analysis.promotions_detected) if analysis.promotions_detected else "Ninguna detectada"

    return f"""Datos del mercado para el informe diario de {analysis.hotel_name} ({analysis.city}):

POSICIÓN EN EL MERCADO HOY ({analysis.date}):
- Tu precio medio: {analysis.your_avg_price}€
- Media del mercado: {analysis.market_avg_price}€
- Precio más bajo en el mercado: {analysis.market_min_price}€
- Precio más alto: {analysis.market_max_price}€
- Tu posición por precio: #{analysis.your_position_rank} de {analysis.total_competitors} hoteles
- Señal de demanda: {analysis.demand_signal.upper()} — {analysis.demand_reason}
- Presión de precios: {analysis.price_pressure.upper()}

COMPETIDORES RELEVANTES:
{comps_summary}

PROMOCIONES DETECTADAS EN LA COMPETENCIA:
{promos}

RECOMENDACIONES DEL SISTEMA:
{recs_summary}

Escribe el informe diario completo. Incluye:
1. Resumen ejecutivo (2-3 frases: cómo está el mercado hoy)
2. Tu posición y cómo estás vs la competencia
3. Amenazas detectadas (promociones de competidores, etc.)
4. Oportunidades concretas
5. Acciones recomendadas para hoy (específicas y con números)
6. Una frase de cierre con el estado general

No uses markdown, escribe en texto plano con párrafos separados por línea en blanco.
Empieza directamente con el contenido, sin "Estimado director" ni saludos."""


def generate_report_text(analysis: DailyAnalysis, api_key: str) -> str:
    """Llama a Claude API para generar el texto del informe."""
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_analysis_prompt(analysis)}]
    )
    return message.content[0].text


# ──────────────────────────────────────────────
# 2. Plantilla HTML del email
# ──────────────────────────────────────────────

def build_email_html(analysis: DailyAnalysis, report_text: str) -> str:
    """Construye el HTML del email con diseño profesional."""

    demand_color = {"alta": "#0F6E56", "media": "#BA7517", "baja": "#993C1D"}[analysis.demand_signal]
    demand_bg = {"alta": "#E1F5EE", "media": "#FAEEDA", "baja": "#FAECE7"}[analysis.demand_signal]

    pressure_label = {"subir": "↑ Subir precios", "bajar": "↓ Bajar precios", "mantener": "→ Mantener"}[analysis.price_pressure]
    pressure_color = {"subir": "#0F6E56", "bajar": "#993C1D", "mantener": "#444441"}[analysis.price_pressure]

    # Filas de competidores
    comp_rows = ""
    for c in analysis.competitors[:6]:
        diff_str = f"{c.price_diff_pct:+.1f}%"
        diff_color = "#0F6E56" if c.price_diff_pct > 0 else "#993C1D"
        promo_badge = '<span style="background:#FAECE7;color:#993C1D;font-size:11px;padding:2px 6px;border-radius:4px;margin-left:6px;">PROMO</span>' if c.is_promotion else ""
        comp_rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #f0ede8;font-size:14px;color:#2C2C2A;">{c.name[:35]}{promo_badge}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f0ede8;font-size:14px;font-weight:600;color:#2C2C2A;">{c.price:.0f}€</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f0ede8;font-size:13px;color:{diff_color};">{diff_str}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f0ede8;font-size:13px;color:#888780;">{c.review_score or '—'}</td>
        </tr>"""

    # Filas de recomendaciones
    rec_rows = ""
    urgency_colors = {"alta": "#993C1D", "media": "#BA7517", "baja": "#3B6D11"}
    urgency_bg = {"alta": "#FAECE7", "media": "#FAEEDA", "baja": "#EAF3DE"}
    for r in analysis.recommendations:
        arrow = "↑" if r.change_pct > 0 else ("↓" if r.change_pct < 0 else "→")
        arrow_color = "#0F6E56" if r.change_pct > 0 else ("#993C1D" if r.change_pct < 0 else "#444441")
        urg_c = urgency_colors.get(r.urgency, "#444441")
        urg_b = urgency_bg.get(r.urgency, "#f0ede8")
        rec_rows += f"""
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #f0ede8;font-size:14px;color:#2C2C2A;font-weight:500;">{r.room_type}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #f0ede8;font-size:14px;color:#2C2C2A;">{r.current_price:.0f}€</td>
          <td style="padding:10px 12px;border-bottom:1px solid #f0ede8;font-size:15px;font-weight:700;color:{arrow_color};">{arrow} {r.recommended_price:.0f}€</td>
          <td style="padding:10px 12px;border-bottom:1px solid #f0ede8;font-size:12px;">
            <span style="background:{urg_b};color:{urg_c};padding:2px 8px;border-radius:10px;">{r.urgency}</span>
          </td>
        </tr>"""

    # Texto del informe: convertir saltos de línea en párrafos
    paragraphs = ""
    for para in report_text.strip().split("\n\n"):
        if para.strip():
            paragraphs += f'<p style="margin:0 0 14px;font-size:15px;line-height:1.7;color:#2C2C2A;">{para.strip()}</p>'

    date_str = datetime.now().strftime("%A, %d de %B de %Y").capitalize()

    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>RevMax Daily — {analysis.hotel_name}</title></head>
<body style="margin:0;padding:0;background:#F5F3EE;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">

<div style="max-width:620px;margin:24px auto;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #E8E5DF;">

  <!-- Header -->
  <div style="background:#1D2B1D;padding:28px 32px;">
    <div style="display:flex;align-items:center;justify-content:space-between;">
      <div>
        <div style="font-size:11px;color:#5DCAA5;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;">RevMax Daily</div>
        <div style="font-size:22px;font-weight:600;color:#ffffff;">{analysis.hotel_name}</div>
        <div style="font-size:13px;color:#9FE1CB;margin-top:2px;">{date_str}</div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:32px;font-weight:700;color:#5DCAA5;">{analysis.your_avg_price:.0f}€</div>
        <div style="font-size:12px;color:#9FE1CB;">tu precio medio</div>
      </div>
    </div>
  </div>

  <!-- KPI bar -->
  <div style="background:#F5F3EE;padding:16px 32px;display:flex;gap:0;border-bottom:1px solid #E8E5DF;">
    <div style="flex:1;text-align:center;border-right:1px solid #E8E5DF;">
      <div style="font-size:11px;color:#888780;text-transform:uppercase;letter-spacing:0.06em;">Media mercado</div>
      <div style="font-size:20px;font-weight:600;color:#2C2C2A;margin-top:2px;">{analysis.market_avg_price:.0f}€</div>
    </div>
    <div style="flex:1;text-align:center;border-right:1px solid #E8E5DF;">
      <div style="font-size:11px;color:#888780;text-transform:uppercase;letter-spacing:0.06em;">Tu posición</div>
      <div style="font-size:20px;font-weight:600;color:#2C2C2A;margin-top:2px;">#{analysis.your_position_rank} / {analysis.total_competitors}</div>
    </div>
    <div style="flex:1;text-align:center;border-right:1px solid #E8E5DF;">
      <div style="font-size:11px;color:#888780;text-transform:uppercase;letter-spacing:0.06em;">Demanda</div>
      <div style="font-size:15px;font-weight:600;margin-top:4px;padding:2px 10px;border-radius:6px;display:inline-block;background:{demand_bg};color:{demand_color};">{analysis.demand_signal.upper()}</div>
    </div>
    <div style="flex:1;text-align:center;">
      <div style="font-size:11px;color:#888780;text-transform:uppercase;letter-spacing:0.06em;">Acción</div>
      <div style="font-size:14px;font-weight:600;color:{pressure_color};margin-top:6px;">{pressure_label}</div>
    </div>
  </div>

  <div style="padding:28px 32px;">

    <!-- Análisis IA -->
    <h2 style="font-size:13px;font-weight:600;color:#888780;text-transform:uppercase;letter-spacing:0.06em;margin:0 0 16px;">Análisis del día</h2>
    {paragraphs}

    <!-- Competencia -->
    <h2 style="font-size:13px;font-weight:600;color:#888780;text-transform:uppercase;letter-spacing:0.06em;margin:28px 0 12px;">Competencia</h2>
    <table style="width:100%;border-collapse:collapse;border:1px solid #E8E5DF;border-radius:8px;overflow:hidden;">
      <thead>
        <tr style="background:#F5F3EE;">
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#888780;font-weight:600;">Hotel</th>
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#888780;font-weight:600;">Precio</th>
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#888780;font-weight:600;">Vs tú</th>
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#888780;font-weight:600;">Score</th>
        </tr>
      </thead>
      <tbody>{comp_rows}</tbody>
    </table>

    <!-- Recomendaciones -->
    <h2 style="font-size:13px;font-weight:600;color:#888780;text-transform:uppercase;letter-spacing:0.06em;margin:28px 0 12px;">Precios recomendados para hoy</h2>
    <table style="width:100%;border-collapse:collapse;border:1px solid #E8E5DF;border-radius:8px;overflow:hidden;">
      <thead>
        <tr style="background:#F5F3EE;">
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#888780;font-weight:600;">Tipo habitación</th>
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#888780;font-weight:600;">Precio actual</th>
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#888780;font-weight:600;">Recomendado</th>
          <th style="padding:10px 12px;text-align:left;font-size:12px;color:#888780;font-weight:600;">Urgencia</th>
        </tr>
      </thead>
      <tbody>{rec_rows}</tbody>
    </table>

  </div>

  <!-- Footer -->
  <div style="background:#F5F3EE;padding:16px 32px;border-top:1px solid #E8E5DF;text-align:center;">
    <p style="margin:0;font-size:12px;color:#888780;">RevMax Daily · Informe generado automáticamente · {datetime.now().strftime('%H:%M')}</p>
    <p style="margin:4px 0 0;font-size:12px;color:#B4B2A9;">Para cambiar preferencias o pausar informes, responde a este email.</p>
  </div>

</div>
</body>
</html>"""


# ──────────────────────────────────────────────
# 3. Envío por email (Gmail / SMTP)
# ──────────────────────────────────────────────

def send_email(
    html_content: str,
    subject: str,
    to_email: str,
    from_email: str,
    smtp_password: str,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
):
    """Envía el email usando SMTP (compatible con Gmail y la mayoría de proveedores)."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"RevMax Daily <{from_email}>"
    msg["To"] = to_email

    part = MIMEText(html_content, "html", "utf-8")
    msg.attach(part)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(from_email, smtp_password)
        server.sendmail(from_email, to_email, msg.as_string())

    print(f"✓ Email enviado a {to_email}")


# ──────────────────────────────────────────────
# 4. Función principal
# ──────────────────────────────────────────────

def generate_and_send(
    analysis: DailyAnalysis,
    config_path: str = "config.json",
):
    """Lee config, genera informe con IA y lo manda."""
    with open(config_path, "r") as f:
        cfg = json.load(f)

    # Claves necesarias en config.json
    anthropic_key = cfg.get("anthropic_api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
    smtp_email = cfg.get("smtp_email", "")
    smtp_password = cfg.get("smtp_password", "")
    recipient = cfg.get("report_recipient", smtp_email)

    if not anthropic_key:
        raise ValueError("Falta anthropic_api_key en config.json")
    if not smtp_email:
        raise ValueError("Falta smtp_email en config.json")

    print("Generando informe con IA...")
    report_text = generate_report_text(analysis, anthropic_key)

    print("Construyendo email HTML...")
    html = build_email_html(analysis, report_text)

    subject = (
        f"RevMax · {analysis.hotel_name} · "
        f"{analysis.demand_signal.capitalize()} demanda · "
        f"{analysis.price_pressure.capitalize()} precios — "
        f"{datetime.now().strftime('%d %b')}"
    )

    if smtp_password:
        print("Enviando email...")
        send_email(
            html_content=html,
            subject=subject,
            to_email=recipient,
            from_email=smtp_email,
            smtp_password=smtp_password,
        )
    else:
        # Si no hay SMTP configurado, guardar en archivo
        out = "data/report_preview.html"
        os.makedirs("data", exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✓ Informe guardado en {out} (abre en tu navegador para ver el diseño)")

    return html, report_text
