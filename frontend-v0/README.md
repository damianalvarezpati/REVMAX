# RevMax Frontend (v0 export) — Candidato principal

Frontend exportado desde v0, conectado al backend real RevMax. **La pantalla Analysis usa datos reales** (POST /api/run-analysis y GET /api/job-status/{job_id}). El resto de pantallas (Dashboard, Clients, Reports, Alerts, Dojo, Settings) siguen usando mocks por ahora.

## Cómo arrancar

### Backend (puerto 8001)

En la **raíz del proyecto RevMax** (no dentro de frontend-v0):

```bash
python -m uvicorn admin_panel:app --host 127.0.0.1 --port 8001
```

### Frontend (puerto 3000)

En esta carpeta:

```bash
npm install
npm run dev
```

Abre **http://localhost:3000**. La ruta `/` es la pantalla Analysis.

### Conexión al backend

En desarrollo, las peticiones a `/api/*` se reenvían al backend mediante **rewrites** de Next.js (ver `next.config.mjs`). Por defecto el destino es `http://127.0.0.1:8001`. Si tu backend está en otra URL, crea un `.env.local` en esta carpeta:

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
