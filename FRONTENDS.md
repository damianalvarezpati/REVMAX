# Frontends RevMax — Arquitectura

## FRONTEND PRINCIPAL OFICIAL: `frontend-v0/`

**Este es el frontend que debes usar y desarrollar.** No hay ambigüedad.

- **Ruta:** `frontend-v0/`
- **Stack:** Next.js (export real de v0)
- **Puerto en desarrollo:** 3000 → **http://localhost:3000**
- **Backend:** FastAPI en puerto **8001** (peticiones `/api/*` se reenvían vía rewrites de Next.js)
- **Analysis:** Conectada al backend real (POST /api/run-analysis, GET /api/job-status/{job_id})
- **Arranque:** Ver `frontend-v0/README.md` o usar **`start_revmax.command`** (doble clic) para backend + frontend-v0

**A partir de ahora:** edita y desarrolla en **frontend-v0**. El resto son fallbacks.

---

## FRONTENDS SECUNDARIOS (legacy / fallback)

### `operator_console/`

- **Uso:** Legacy. UI antigua (HTML estático servido por FastAPI en GET / cuando abres http://localhost:8001).
- **Estado:** No es la UI principal. Mantenida por compatibilidad; puede quedar obsoleta cuando el build de frontend-v0 se sirva desde el backend.
- **Cuándo usarla:** Solo si necesitas la consola antigua sin Node/npm (por ejemplo solo backend en 8001).

### `frontend/`

- **Uso:** Experimental / fallback técnico. Vite + React, Analysis conectada al backend.
- **Estado:** No es la UI principal. Útil si necesitas una UI mínima sin Next.js.
- **Cuándo usarla:** Solo como alternativa técnica (sin Next.js); no como base de producto.

---

## Resumen

| Carpeta            | Rol              | ¿Editar?                          |
|--------------------|------------------|-----------------------------------|
| **frontend-v0/**   | Principal oficial| **Sí** — aquí se desarrolla       |
| **frontend/**      | Fallback técnico | No (salvo necesidad concreta)      |
| **operator_console/** | Legacy        | No — quedará obsoleta a futuro    |

---

## Cómo arrancar

- **UI principal (recomendado):** doble clic en **`start_revmax.command`** → backend + frontend-v0 + navegador en http://localhost:3000
- **Solo backend (UI legacy en 8001):** `python -m uvicorn admin_panel:app --host 127.0.0.1 --port 8001` y abrir http://localhost:8001
