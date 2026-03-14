#!/bin/bash
# RevMax — Doble clic para abrir el panel de administración
# Ejecuta este archivo con doble clic (o desde Terminal)

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "No se encontró el entorno virtual (.venv)."
  echo "Ejecuta primero: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  echo "Luego: playwright install chromium"
  read -p "Pulsa Enter para cerrar..."
  exit 1
fi

source .venv/bin/activate

echo ""
echo "  RevMax — Panel de administración"
echo "  ================================="
echo ""
echo "  Abre en tu navegador: http://localhost:8001"
echo ""
echo "  (Para cerrar el panel: Ctrl+C o cierra esta ventana)"
echo ""

# Abrir el navegador automáticamente tras 2 segundos
(sleep 2 && open "http://localhost:8001" 2>/dev/null) &

python3 admin_panel.py
