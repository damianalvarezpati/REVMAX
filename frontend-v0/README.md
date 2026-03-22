# RevMax — Frontend principal oficial (frontend-v0)

**Este es el frontend principal y oficial de RevMax.** Desarrollo y UX se hacen aquí.

- **Puerto:** 3000 → **http://localhost:3000**
- **Backend:** 8001 (FastAPI). Las peticiones `/api/*` se reenvían al backend vía rewrites (ver `next.config.mjs`).
- **Analysis:** Conectada al backend real (POST /api/run-analysis, GET /api/job-status/{job_id}).
- **Calidad / definición de terminado:** [SHOKUN](../docs/shokun/README.md) (repo).

## Arranque rápido (recomendado)

En la **raíz del proyecto** (no aquí), doble clic en **`start_revmax.command`** para levantar backend + frontend-v0 y abrir el navegador. Primero: `chmod +x start_revmax.command stop_revmax.command`.

## Arranque manual

### 1. Backend (puerto 8001)

En la **raíz del proyecto RevMax**:

```bash
python -m uvicorn admin_panel:app --host 127.0.0.1 --port 8001
```

### 2. Frontend (puerto 3000)

En esta carpeta (`frontend-v0/`):

```bash
npm install
npm run dev
```

Abre **http://localhost:3000**. La ruta `/` es la pantalla Analysis.

### Variable de entorno (opcional)

Por defecto los rewrites apuntan a `http://127.0.0.1:8001`. Si el backend está en otra URL, crea `.env.local` (o copia `.env.example`):

```
NEXT_PUBLIC_REVMAX_API_URL=http://localhost:8001
```

## Qué está conectado al backend (datos reales)

- **Pantalla Analysis** (`app/page.tsx`):
  - Formulario: nombre del hotel, ciudad, modo Demo.
  - Botón **Run Analysis** → `POST /api/run-analysis`.
  - Polling a `GET /api/job-status/{job_id}` cada 2 s.
  - Estados de UI: idle, running, completed, failed, stalled, degraded.
  - Cuando termina, se rellenan con datos reales:
    - Hero (recomendación, confianza, resumen)
    - Market Snapshot, Market Context, Events, Distribution & Parity
    - Comp Set, Recommended Action, Confidence & Quality
    - Progress (9 pasos)

Los datos de Analysis **ya no vienen de** `lib/mock-data.ts`; se construyen desde la respuesta del backend en `lib/analysis-from-job.ts`.

## Qué sigue mockeado

- **Dashboard**, **Clients**, **Reports**, **Alerts**, **Dojo**, **Settings**: siguen usando `lib/mock-data.ts` y no llaman al backend.
- Dentro de Analysis, el mensaje rotativo de “Analysis Progress” mientras corre el job sigue usando `statusMessages` de mock-data (solo texto; no afecta a los datos del análisis).

## Estructura relevante

- `app/page.tsx` — Página principal Analysis (flujo real).
- `components/analysis/*` — Componentes de la pantalla Analysis (reciben datos mapeados del job).
- `lib/revmax-api.ts` — Cliente API (runAnalysis, getJobStatus).
- `lib/analysis-from-job.ts` — Mapeo job-status → formato de componentes (AnalysisResult).
- `lib/config.ts` — URL base del API (NEXT_PUBLIC_REVMAX_API_URL).
