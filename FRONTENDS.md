# Frontends RevMax

## Candidato principal: `frontend-v0/`

**frontend-v0/** es el frontend principal candidato. Es el export real de v0 (Next.js) con:

- Pantalla **Analysis** conectada al backend real (POST /api/run-analysis, GET /api/job-status/{job_id}).
- Dashboard, Clients, Reports, Alerts, Dojo, Settings (por ahora con mocks).

Para arrancarlo: ver `frontend-v0/README.md`. Backend en puerto 8001, frontend en 3000.

## Fallback / legado

- **frontend/** — Frontend improvisado (Vite + React) con Analysis conectada al backend. Queda como fallback por si se necesita una UI mínima sin Next.js.
- **operator_console/** — UI antigua (operator_ui.html servida por admin_panel en GET /). Sigue disponible en http://localhost:8001 al arrancar el backend.

No se ha eliminado ninguno; el desarrollo prioritario es **frontend-v0** con la pantalla Analysis ya real.
