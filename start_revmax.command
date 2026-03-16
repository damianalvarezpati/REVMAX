#!/bin/bash
# RevMax — Lanzador principal (doble clic)
# Arranca backend (8001) + frontend-v0 (3000) y abre el navegador.
# Para parar: doble clic en stop_revmax.command o pulsa Enter en esta ventana.

set -e
REVMAX_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REVMAX_ROOT"

LOG_BACKEND="/tmp/revmax_backend.log"
LOG_FRONTEND="/tmp/revmax_frontend.log"

echo ""
echo "  RevMax — UI principal (frontend-v0)"
echo "  ===================================="
echo ""

# Activar venv si existe
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

# Backend
echo "  Iniciando backend (puerto 8001)..."
python3 -m uvicorn admin_panel:app --host 127.0.0.1 --port 8001 >> "$LOG_BACKEND" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > /tmp/revmax_backend.pid

# Dar tiempo a que el backend arranque
sleep 2

# Frontend (frontend-v0)
if [ ! -d "frontend-v0" ]; then
  echo "  Error: no se encontró frontend-v0/"
  kill $BACKEND_PID 2>/dev/null || true
  read -p "  Pulsa Enter para cerrar..."
  exit 1
fi

if ! command -v npm &>/dev/null; then
  echo "  Error: npm no encontrado. Instala Node.js (https://nodejs.org) y vuelve a intentar."
  kill $BACKEND_PID 2>/dev/null || true
  read -p "  Pulsa Enter para cerrar..."
  exit 1
fi

if [ ! -d "frontend-v0/node_modules" ]; then
  echo "  Primera vez: instalando dependencias de frontend-v0..."
  (cd frontend-v0 && npm install)
fi

echo "  Iniciando frontend-v0 (puerto 3000)..."
(cd frontend-v0 && npm run dev >> "$LOG_FRONTEND" 2>&1) &
FRONTEND_PID=$!
echo $FRONTEND_PID > /tmp/revmax_frontend.pid

# Esperar a que Next esté listo
sleep 5

echo "  Abriendo navegador en http://localhost:3000"
open "http://localhost:3000" 2>/dev/null || true

echo ""
echo "  Backend:  http://localhost:8001  (API)"
echo "  Frontend: http://localhost:3000  (UI principal)"
echo ""
echo "  Logs: $LOG_BACKEND y $LOG_FRONTEND"
echo ""
echo "  Pulsa Enter aquí para PARAR backend y frontend..."
read

# Parar: matar por puerto (más fiable que solo el PID del padre)
echo "  Parando servicios..."
for port in 3000 8001; do
  PIDS=$(lsof -ti :$port 2>/dev/null) || true
  if [ -n "$PIDS" ]; then
    echo "$PIDS" | xargs kill -9 2>/dev/null || true
  fi
done
rm -f /tmp/revmax_backend.pid /tmp/revmax_frontend.pid
echo "  Listo."
sleep 1
