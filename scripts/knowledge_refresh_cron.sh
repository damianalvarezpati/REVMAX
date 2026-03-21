#!/usr/bin/env bash
# Cron nocturno (ej. 3:15): 15 3 * * * /ruta/a/revmax/scripts/knowledge_refresh_cron.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec python3 knowledge_refresh.py scheduled
