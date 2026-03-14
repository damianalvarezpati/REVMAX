#!/usr/bin/env python3
"""
RevMax — Asistente de configuración inicial
Crea tu config.json paso a paso con preguntas simples.
"""

import json
import os


def ask(prompt: str, default: str = "") -> str:
    full = f"{prompt} [{default}]: " if default else f"{prompt}: "
    val = input(full).strip()
    return val if val else default


def ask_float(prompt: str, default: float) -> float:
    while True:
        val = ask(prompt, str(default))
        try:
            return float(val)
        except ValueError:
            print("  Por favor introduce un número (ej: 120.0)")


def ask_list(prompt: str) -> list[str]:
    print(f"{prompt} (separa con comas):")
    val = input("  > ").strip()
    return [x.strip() for x in val.split(",") if x.strip()]


def main():
    print("\n" + "="*55)
    print("  RevMax — Configuración inicial")
    print("="*55)
    print("\nVamos a configurar tu hotel en 2 minutos.\n")

    config = {}

    # Info del hotel
    print("── Tu hotel ──────────────────────────────────")
    config["name"] = ask("Nombre exacto del hotel en Booking.com")
    config["city"] = ask("Ciudad (ej: Barcelona, Madrid, Sevilla)")
    config["stars"] = int(ask_float("Número de estrellas (1-5)", 4))

    # Tipos de habitación y precios
    print("\n── Tipos de habitación ───────────────────────")
    print("Escribe los tipos de habitación que tienes.")
    room_types = ask_list("Tipos (ej: doble estándar, suite junior, habitación familiar)")
    if not room_types:
        room_types = ["doble estándar"]

    print("\nAhora el precio base por noche de cada tipo:")
    base_prices = {}
    for rt in room_types:
        price = ask_float(f"  Precio base de '{rt}' (€)", 100.0)
        base_prices[rt] = price
    config["room_types"] = room_types
    config["base_prices"] = base_prices

    # Competidores
    print("\n── Competidores a vigilar ────────────────────")
    print("Escribe los nombres (o parte del nombre) de tus principales competidores.")
    competitors = ask_list("Competidores")
    config["competitor_names"] = competitors if competitors else []

    # Configuración de precios
    print("\n── Límites de precio ─────────────────────────")
    config["min_price"] = ask_float("Precio mínimo absoluto (€) — nunca bajarás de aquí", 50.0)
    config["max_price"] = ask_float("Precio máximo absoluto (€) — nunca subirás de aquí", 500.0)
    config["target_occupancy"] = ask_float("Ocupación objetivo (0.0–1.0, ej: 0.80 = 80%)", 0.80)

    # API de IA
    print("\n── Clave de API de IA ────────────────────────")
    print("Necesitas una clave de Anthropic Claude para generar los informes.")
    print("Consíguela gratis en: https://console.anthropic.com")
    config["anthropic_api_key"] = ask("Tu clave de API (empieza por 'sk-ant-...')", "")

    # Email
    print("\n── Configuración de email ────────────────────")
    print("RevMax usará tu email de Gmail para enviar los informes.")
    print("Necesitas activar 'Contraseñas de aplicación' en tu cuenta Google.")
    print("Guía: https://support.google.com/accounts/answer/185833\n")

    config["smtp_email"] = ask("Tu dirección de Gmail (ej: tuemail@gmail.com)", "")
    config["smtp_password"] = ask("Contraseña de aplicación de Gmail (16 caracteres)", "")
    config["report_recipient"] = ask(
        "Email destinatario del informe",
        config["smtp_email"]
    )

    # Horario
    print("\n── Horario de envío ──────────────────────────")
    config["schedule_time"] = ask("Hora de envío diario (formato HH:MM)", "07:30")

    # Guardar
    path = "config.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*55}")
    print(f"  ✓ Configuración guardada en {path}")
    print(f"{'='*55}")
    print(f"""
Próximos pasos:
  1. Prueba el sistema:
     python run_revmax.py --preview

  2. Si el preview se ve bien, activa el envío diario:
     python scheduler.py

  3. El informe llegará cada día a las {config['schedule_time']} a:
     {config['report_recipient']}

Si tienes algún problema, edita config.json directamente.
""")


if __name__ == "__main__":
    main()
