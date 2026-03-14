"""
RevMax — Email HTML v2
Construye el email ejecutivo usando el output completo del sistema multi-agente.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


def build_email_html_v2(full_analysis: dict, report_data: dict) -> str:
    hotel_name = full_analysis.get("hotel_name", "Tu Hotel")
    date_str = datetime.now().strftime("%A, %d de %B de %Y").capitalize()
    outputs = full_analysis.get("agent_outputs", {})
    briefing = full_analysis.get("briefing", {})

    discovery = outputs.get("discovery", {})
    pricing = outputs.get("pricing", {})
    demand = outputs.get("demand", {})
    reputation = outputs.get("reputation", {})
    distribution = outputs.get("distribution", {})
    compset = outputs.get("compset", {})

    # KPIs principales
    your_adr = discovery.get("adr_double", "—")
    market_avg = compset.get("compset_summary", {}).get("primary_avg_adr", "—")
    your_rank = pricing.get("market_context", {}).get("your_position_rank", "—")
    total_comp = pricing.get("market_context", {}).get("total_compset", "—")
    ari = pricing.get("indices", {}).get("ari", {}).get("value", "—")
    rgi = pricing.get("indices", {}).get("rgi", {}).get("value", "—")
    demand_score = demand.get("demand_index", {}).get("score", "—")
    demand_signal = demand.get("demand_index", {}).get("signal", "medium")
    gri = reputation.get("gri", {}).get("value", "—")
    visibility = distribution.get("visibility_score", "—")
    booking_pos = distribution.get("booking_audit", {}).get("search_position", "—")

    overall_status = report_data.get("overall_status", "stable")
    report_text = report_data.get("report_text", "")
    priority_actions = report_data.get("priority_actions", [])
    watchlist = report_data.get("weekly_watchlist", "")
    system_confidence = briefing.get("system_confidence", 0.7)
    conflicts = briefing.get("conflicts", [])

    # Colores por estado
    status_colors = {
        "strong":           {"bg": "#E1F5EE", "text": "#085041", "label": "Fuerte"},
        "stable":           {"bg": "#E6F1FB", "text": "#0C447C", "label": "Estable"},
        "needs_attention":  {"bg": "#FAEEDA", "text": "#633806", "label": "Atención"},
        "alert":            {"bg": "#FAECE7", "text": "#712B13", "label": "Alerta"},
    }
    sc = status_colors.get(overall_status, status_colors["stable"])

    demand_colors = {
        "very_high": "#0F6E56", "high": "#1D9E75",
        "medium": "#BA7517", "low": "#D85A30", "very_low": "#993C1D"
    }
    demand_color = demand_colors.get(demand_signal, "#BA7517")

    # Texto del informe → párrafos HTML
    paragraphs_html = "".join(
        f'<p style="margin:0 0 12px;font-size:14px;line-height:1.75;color:#2C2C2A;">{p.strip()}</p>'
        for p in (report_text or "").split("\n\n") if p.strip()
    )

    # Acciones prioritarias
    urgency_colors = {
        "immediate": {"bg": "#FAECE7", "text": "#712B13", "dot": "#D85A30", "label": "Urgente hoy"},
        "this_week":  {"bg": "#FAEEDA", "text": "#633806", "dot": "#BA7517", "label": "Esta semana"},
        "this_month": {"bg": "#EAF3DE", "text": "#27500A", "dot": "#3B6D11", "label": "Este mes"},
    }
    actions_html = ""
    for a in priority_actions[:3]:
        urg = a.get("urgency", "this_week")
        uc = urgency_colors.get(urg, urgency_colors["this_week"])
        actions_html += f"""
        <tr>
          <td style="padding:14px 16px;border-bottom:1px solid #EDE9E0;vertical-align:top;">
            <div style="display:flex;align-items:flex-start;gap:12px;">
              <div style="width:8px;height:8px;border-radius:50%;background:{uc['dot']};margin-top:5px;flex-shrink:0;"></div>
              <div style="flex:1;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                  <span style="font-size:13px;font-weight:600;color:#1D2B1D;">#{a.get('rank','?')} — {a.get('action','')}</span>
                  <span style="background:{uc['bg']};color:{uc['text']};font-size:10px;padding:2px 7px;border-radius:20px;font-weight:500;">{uc['label']}</span>
                </div>
                <div style="font-size:13px;color:#5F5E5A;margin-bottom:3px;">{a.get('reason','')}</div>
                <div style="font-size:12px;color:#9FE1CB;font-weight:500;">{a.get('expected_impact','')}</div>
              </div>
            </div>
          </td>
        </tr>"""

    # Compset tabla
    primary_compset = compset.get("compset", {}).get("primary", [])[:5]
    compset_rows = ""
    your_adr_num = your_adr if isinstance(your_adr, (int, float)) else 0
    for h in primary_compset:
        h_price = h.get("adr_double") or h.get("last_price_checked") or 0
        diff = ((h_price - your_adr_num) / your_adr_num * 100) if your_adr_num and h_price else 0
        diff_color = "#0F6E56" if diff > 0 else "#993C1D"
        promo_badge = '<span style="background:#FAECE7;color:#993C1D;font-size:10px;padding:1px 6px;border-radius:4px;margin-left:4px;">PROMO</span>' if h.get("promotions_active") else ""
        compset_rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #EDE9E0;font-size:13px;color:#2C2C2A;">{h.get('name','?')[:30]}{promo_badge}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #EDE9E0;font-size:13px;font-weight:600;">{h_price:.0f}€</td>
          <td style="padding:8px 12px;border-bottom:1px solid #EDE9E0;font-size:12px;color:{diff_color};">{diff:+.1f}%</td>
          <td style="padding:8px 12px;border-bottom:1px solid #EDE9E0;font-size:12px;color:#888780;">{h.get('booking_score','—')}</td>
        </tr>"""

    # Conflictos
    conflicts_html = ""
    for c in conflicts:
        sev_colors = {"high": "#FAECE7", "medium": "#FAEEDA"}
        sev_text = {"high": "#712B13", "medium": "#633806"}
        bg = sev_colors.get(c.get("severity", "medium"), "#FAEEDA")
        tc = sev_text.get(c.get("severity", "medium"), "#633806")
        conflicts_html += f"""
        <div style="background:{bg};border-radius:6px;padding:10px 12px;margin-bottom:6px;font-size:13px;color:{tc};">
          <strong>⚠ {c.get('description','')}</strong><br>
          <span style="font-size:12px;">→ {c.get('resolution_hint','')}</span>
        </div>"""

    # Confidence badge
    conf_pct = int(system_confidence * 100)
    conf_color = "#0F6E56" if conf_pct >= 80 else ("#BA7517" if conf_pct >= 65 else "#993C1D")

    ari_display = f"{ari:.2f}" if isinstance(ari, float) else str(ari)
    rgi_display = f"{rgi:.2f}" if isinstance(rgi, float) else str(rgi)
    vis_display = f"{visibility:.0%}" if isinstance(visibility, float) else str(visibility)
    gri_display = f"{gri:.1f}" if isinstance(gri, float) else str(gri)

    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>RevMax Daily — {hotel_name}</title></head>
<body style="margin:0;padding:0;background:#F0EDE6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,sans-serif;">

<div style="max-width:640px;margin:20px auto;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #DDD9D0;">

  <!-- HEADER -->
  <div style="background:#1D2B1D;padding:28px 32px 24px;">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;">
      <div>
        <div style="font-size:10px;color:#5DCAA5;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px;">RevMax Daily · Revenue Manager Virtual</div>
        <div style="font-size:22px;font-weight:700;color:#ffffff;margin-bottom:3px;">{hotel_name}</div>
        <div style="font-size:13px;color:#9FE1CB;">{date_str}</div>
      </div>
      <div style="text-align:right;">
        <div style="background:{sc['bg']};color:{sc['text']};font-size:12px;font-weight:700;padding:4px 12px;border-radius:20px;margin-bottom:8px;display:inline-block;">{sc['label'].upper()}</div>
        <div style="font-size:36px;font-weight:700;color:#5DCAA5;line-height:1;">{your_adr if isinstance(your_adr,(int,float)) else '—'}€</div>
        <div style="font-size:11px;color:#9FE1CB;">tu precio medio/noche</div>
      </div>
    </div>
  </div>

  <!-- KPI BAR -->
  <div style="background:#F5F2EB;border-bottom:1px solid #DDD9D0;padding:0;">
    <table style="width:100%;border-collapse:collapse;">
      <tr>
        <td style="padding:14px 0;text-align:center;border-right:1px solid #DDD9D0;">
          <div style="font-size:10px;color:#888780;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">Media compset</div>
          <div style="font-size:19px;font-weight:700;color:#2C2C2A;">{market_avg if isinstance(market_avg,(int,float)) else '—'}€</div>
        </td>
        <td style="padding:14px 0;text-align:center;border-right:1px solid #DDD9D0;">
          <div style="font-size:10px;color:#888780;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">Posición precio</div>
          <div style="font-size:19px;font-weight:700;color:#2C2C2A;">#{your_rank}/{total_comp}</div>
        </td>
        <td style="padding:14px 0;text-align:center;border-right:1px solid #DDD9D0;">
          <div style="font-size:10px;color:#888780;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">ARI · RGI</div>
          <div style="font-size:19px;font-weight:700;color:#2C2C2A;">{ari_display} · {rgi_display}</div>
        </td>
        <td style="padding:14px 0;text-align:center;">
          <div style="font-size:10px;color:#888780;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">Demanda</div>
          <div style="font-size:14px;font-weight:700;color:{demand_color};background:{demand_color}18;padding:2px 10px;border-radius:10px;display:inline-block;">{demand_score}/100</div>
        </td>
      </tr>
      <tr>
        <td style="padding:10px 0;text-align:center;border-right:1px solid #DDD9D0;border-top:1px solid #DDD9D0;">
          <div style="font-size:10px;color:#888780;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">GRI reputación</div>
          <div style="font-size:17px;font-weight:700;color:#2C2C2A;">{gri_display}</div>
        </td>
        <td style="padding:10px 0;text-align:center;border-right:1px solid #DDD9D0;border-top:1px solid #DDD9D0;">
          <div style="font-size:10px;color:#888780;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">Pos. Booking</div>
          <div style="font-size:17px;font-weight:700;color:#2C2C2A;">#{booking_pos}</div>
        </td>
        <td style="padding:10px 0;text-align:center;border-right:1px solid #DDD9D0;border-top:1px solid #DDD9D0;">
          <div style="font-size:10px;color:#888780;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">Visibilidad</div>
          <div style="font-size:17px;font-weight:700;color:#2C2C2A;">{vis_display}</div>
        </td>
        <td style="padding:10px 0;text-align:center;border-top:1px solid #DDD9D0;">
          <div style="font-size:10px;color:#888780;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">Confidence IA</div>
          <div style="font-size:17px;font-weight:700;color:{conf_color};">{conf_pct}%</div>
        </td>
      </tr>
    </table>
  </div>

  <div style="padding:28px 32px;">

    <!-- ANÁLISIS -->
    <div style="margin-bottom:24px;">
      <div style="font-size:10px;font-weight:700;color:#888780;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:14px;">Análisis del día</div>
      {paragraphs_html}
    </div>

    <!-- CONFLICTOS (si los hay) -->
    {"<div style='margin-bottom:20px;'><div style='font-size:10px;font-weight:700;color:#888780;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px;'>Conflictos detectados entre señales</div>" + conflicts_html + "</div>" if conflicts_html else ""}

    <!-- ACCIONES PRIORITARIAS -->
    <div style="margin-bottom:24px;">
      <div style="font-size:10px;font-weight:700;color:#888780;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:14px;">Las 3 acciones de hoy</div>
      <table style="width:100%;border-collapse:collapse;border:1px solid #DDD9D0;border-radius:10px;overflow:hidden;">
        <tbody>{actions_html}</tbody>
      </table>
    </div>

    <!-- COMPETENCIA -->
    {"<div style='margin-bottom:24px;'><div style='font-size:10px;font-weight:700;color:#888780;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:14px;'>Competencia</div><table style='width:100%;border-collapse:collapse;border:1px solid #DDD9D0;border-radius:10px;overflow:hidden;'><thead><tr style='background:#F5F2EB;'><th style='padding:8px 12px;text-align:left;font-size:11px;color:#888780;font-weight:600;'>Hotel</th><th style='padding:8px 12px;text-align:left;font-size:11px;color:#888780;font-weight:600;'>ADR</th><th style='padding:8px 12px;text-align:left;font-size:11px;color:#888780;font-weight:600;'>Vs tú</th><th style='padding:8px 12px;text-align:left;font-size:11px;color:#888780;font-weight:600;'>Score</th></tr></thead><tbody>" + compset_rows + "</tbody></table></div>" if compset_rows else ""}

    <!-- ALERTA SEMANAL -->
    {"<div style='background:#F5F2EB;border-left:3px solid #1D9E75;border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:24px;font-size:13px;color:#2C2C2A;'><strong>📌 Esta semana:</strong> " + watchlist + "</div>" if watchlist else ""}

  </div>

  <!-- FOOTER -->
  <div style="background:#F5F2EB;border-top:1px solid #DDD9D0;padding:16px 32px;text-align:center;">
    <p style="margin:0 0 4px;font-size:12px;color:#888780;">RevMax Daily · Sistema multi-agente · 7 especialistas IA · {datetime.now().strftime('%H:%M')}</p>
    <p style="margin:0;font-size:11px;color:#B4B2A9;">Para pausar informes o conectar tu PMS, responde a este email.</p>
  </div>

</div>
</body></html>"""


def send_email(html_content, subject, to_email, from_email, smtp_password,
               smtp_host="smtp.gmail.com", smtp_port=587):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"RevMax Daily <{from_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    with smtplib.SMTP(smtp_host, smtp_port) as s:
        s.ehlo()
        s.starttls()
        s.login(from_email, smtp_password)
        s.sendmail(from_email, to_email, msg.as_string())
