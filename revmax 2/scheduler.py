#!/usr/bin/env python3
"""
RevMax — Programador de envíos automáticos
Ejecuta el informe diario a la hora configurada, todos los días.

Uso:
  python scheduler.py          # Inicia en segundo plano
  python scheduler.py --test   # Ejecuta ahora mismo una vez
"""

import schedule
import time
import subprocess
import sys
import json
import os
import argparse
from datetime import datetime


def run_report():
    """Ejecuta el pipeline completo."""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Iniciando informe diario RevMax...")
    try:
        result = subprocess.run(
            [sys.executable, "run_revmax.py"],
            capture_output=False,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        if result.returncode == 0:
            print(f"[{datetime.now().strftime('%H:%M')}] ✓ Informe enviado correctamente")
        else:
            print(f"[{datetime.now().strftime('%H:%M')}] ✗ Error en el informe (código {result.returncode})")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M')}] ✗ Error inesperado: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Ejecutar ahora mismo sin esperar")
    parser.add_argument("--config", default="config.json")
    args = parser.parse_args()

    if args.test:
        print("Ejecutando informe de prueba ahora...")
        run_report()
        return

    # Leer hora de la config
    send_time = "07:30"
    if os.path.exists(args.config):
        with open(args.config) as f:
            cfg = json.load(f)
        send_time = cfg.get("schedule_time", "07:30")

    print(f"\nRevMax Scheduler iniciado")
    print(f"Informe diario programado para las {send_time}")
    print("Deja esta ventana abierta. Pulsa Ctrl+C para detener.\n")

    schedule.every().day.at(send_time).do(run_report)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
