#!/bin/bash
# RevMax — Parar backend y frontend-v0
# Mata procesos en puertos 8001 (backend) y 3000 (frontend-v0).

echo ""
echo "  RevMax — Parando servicios"
echo "  =========================="
echo ""

for port in 3000 8001; do
  PIDS=$(lsof -ti :$port 2>/dev/null) || true
  if [ -n "$PIDS" ]; then
    echo "$PIDS" | xargs kill -9 2>/dev/null || true
    echo "  Puerto $port: procesos terminados."
  else
    echo "  Puerto $port: nada en ejecución."
  fi
done

rm -f /tmp/revmax_backend.pid /tmp/revmax_frontend.pid
echo ""
echo "  Listo."
echo ""
sleep 1
