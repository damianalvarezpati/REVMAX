# frontend/ — Fallback técnico / experimental

**No es la UI principal.** Frontend Vite + React; Analysis conectada al backend.

- **UI principal oficial:** `frontend-v0/` → http://localhost:3000 (arrancar con `start_revmax.command` o `npm run dev` en frontend-v0).
- Esta carpeta es **fallback** por si necesitas una UI mínima sin Next.js. Ver **FRONTENDS.md** en la raíz.

---

## RevMax Frontend (Vite + React)

Frontend React que conecta la pantalla **Analysis** al backend real RevMax.

## Cómo arrancar backend y frontend juntos

### 1. Backend (puerto 8001)

En la raíz del proyecto RevMax:

```bash
# Opcional: activar venv si usas uno
# source .venv/bin/activate  # Linux/macOS

python -m uvicorn admin_panel:app --host 127.0.0.1 --port 8001
```

Abre en el navegador: http://localhost:8001 (UI antigua) o usa el frontend en el puerto 3000.

### 2. Frontend (puerto 3000)

En esta carpeta `frontend/`:

```bash
npm install
npm run dev
```

Abre: http://localhost:3000

El frontend en desarrollo usa el **proxy de Vite**: las peticiones a `/api/*` se reenvían a `http://localhost:8001`. No hace falta configurar `VITE_API_URL` si backend está en 8001.

Si el backend está en otra máquina o puerto, crea un `.env` en `frontend/`:

```
VITE_API_URL=http://localhost:8001
```

(o la URL que corresponda).

## Pantalla Analysis – flujo real

1. **Run analysis**: el usuario introduce nombre del hotel (y opcionalmente ciudad), marca "Demo rápido" si quiere, y pulsa "Run analysis".
2. El frontend llama a **POST /api/run-analysis** con `{ hotel_name, city, hotel_id: 1, fast_demo }`.
3. El backend devuelve `{ ok: true, job_id: "..." }`.
4. El frontend guarda `job_id` y hace **polling** a **GET /api/job-status/{job_id}** cada 2 segundos.
5. Mientras `status` sea activo (`pending`, `running`, etc.), se actualiza:
   - **progress_steps** (9 pasos)
   - **progress_pct**
6. Cuando `status` es terminal (`completed`, `failed`, `stalled`, `cancelled`), se deja de hacer polling y se rellenan:
   - **Hero**: `result_summary.consolidated_action`, `confidence_pct`, `executive_summary`
   - **Market snapshot**: `evidence_found` (hotel_detected, city, own_price, compset_avg, price_position)
   - **Market context**: `result_summary.executive_summary`
   - **Events**: `evidence_found` (demand_score, gri, visibility)
   - **Distribution & parity**: `evidence_found.parity_status`
   - **Comp set**: `evidence_found.top_3_competitors`
   - **Recommended action**: `result_summary.executive_summary`
   - **Confidence & quality**: `analysis_quality` + `result_summary.confidence_pct`

## Estados de la UI

- **idle**: sin análisis en curso; se puede lanzar uno.
- **running**: análisis en curso; se muestra progreso y los 9 pasos.
- **completed**: análisis terminado correctamente; todos los bloques con datos reales.
- **failed**: error o cancelado; se muestra el mensaje del backend.
- **stalled**: job marcado como colgado por el backend.
- **degraded**: completado pero con fallbacks (calidad degradada).

## Qué está conectado al backend

- **Analysis**: 100 % real (POST run-analysis, GET job-status, progreso y resultado).
- Otras pantallas (Dashboard, Clients, Reports, Alerts, Dojo): no están en este frontend aún; solo existe la ruta Analysis.

## Build para producción

```bash
npm run build
```

Los artefactos quedan en `dist/`. Para servirlos detrás del mismo dominio que el backend, puedes configurar el servidor para que sirva el backend en `/api` y el frontend en `/` (por ejemplo con nginx o con FastAPI sirviendo estáticos desde `dist`).
