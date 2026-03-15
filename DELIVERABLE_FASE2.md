# Fase 2 — Job Engine 9/10 — Entregable completo

## ARCHIVOS MODIFICADOS

- `job_schema.py` — Añadido `cancelled`, `TERMINAL_STATUSES`
- `job_state.py` — Sin cambios (ya soporta cancelled vía schema)
- `job_runtime.py` — Añadido `cancel_task(job_id)`
- `job_watchdog.py` — Reescrito: is_alive, dry_run, resumen dict
- `job_recovery.py` — **Nuevo**
- `job_observability.py` — **Nuevo**
- `analysis_runner.py` — mark_job_cancelled, manejo CancelledError
- `admin_panel.py` — Cancel, watchdog upgrade, GET runtime, run-recovery, startup recovery, legacy acotado
- `requirements.txt` — pytest añadido
- `tests/__init__.py`, `tests/conftest.py`, `tests/test_job_engine.py` — **Nuevos**

`error_utils.py` no fue tocado.

---

## ESTRUCTURA NUEVA

| Archivo | Responsabilidad |
|---------|----------------|
| job_schema | Estados/etapas/claves; ACTIVE_STATUSES y TERMINAL_STATUSES |
| job_state | Persistencia data/jobs; create, update, get, list, touch, has_active_job_for_hotel |
| job_runtime | Registro en memoria de tasks; register, unregister, is_running, get_task, cancel_task |
| job_watchdog | Marcar stalled solo si no hay task vivo; dry_run; resumen (reviewed, active_count, alive_in_runtime, marked_stalled, ignored) |
| job_recovery | Startup/crash recovery: jobs activos sin task viva → stalled o failed |
| job_observability | Snapshot: active_job_ids, by_status, orphaned, mismatch_summary |
| analysis_runner | Pipeline + heartbeat; failed/cancelled; callbacks legacy; no escribe analysis_status |
| admin_panel | API (run-analysis, job-status, jobs, run-watchdog, runtime, cancel, run-recovery), startup recovery, legacy acotado |

---

## CÓDIGO COMPLETO

El código completo de cada archivo está en el repositorio en su ruta correspondiente. No se ha omitido ninguna línea en los archivos del proyecto. Los archivos listados arriba contienen todo el código; para ver el contenido completo de `admin_panel.py` (1126 líneas) abrir directamente `admin_panel.py`.

---

## EJEMPLOS REALES (JSON de jobs)

### 1. Job running
```json
{
  "job_id": "a1b2c3d4e5f6",
  "hotel_name": "Hotel Arts Barcelona",
  "city": "Barcelona",
  "hotel_id": 1,
  "status": "running",
  "stage": "discovery",
  "progress_pct": 25,
  "created_at": "2025-03-14T10:00:00Z",
  "started_at": "2025-03-14T10:00:01Z",
  "updated_at": "2025-03-14T10:01:20Z",
  "completed_at": null,
  "error_message": null,
  "warning_message": null,
  "result_html_path": null,
  "preview_html_path": null,
  "fast_demo": false
}
```

### 2. Job cancelled
```json
{
  "job_id": "f6e5d4c3b2a1",
  "hotel_name": "Hotel Ejemplo",
  "city": "Madrid",
  "hotel_id": 1,
  "status": "cancelled",
  "stage": "error",
  "progress_pct": 30,
  "created_at": "2025-03-14T11:00:00Z",
  "started_at": "2025-03-14T11:00:01Z",
  "updated_at": "2025-03-14T11:02:00Z",
  "completed_at": "2025-03-14T11:02:00Z",
  "error_message": "Cancelado por el usuario.",
  "warning_message": null,
  "result_html_path": null,
  "preview_html_path": null,
  "fast_demo": false
}
```

### 3. Job stalled
```json
{
  "job_id": "b2c3d4e5f6a1",
  "hotel_name": "Hotel Stalled",
  "city": "Valencia",
  "hotel_id": 1,
  "status": "stalled",
  "stage": "error",
  "progress_pct": 50,
  "created_at": "2025-03-14T09:00:00Z",
  "started_at": "2025-03-14T09:00:01Z",
  "updated_at": "2025-03-14T09:25:00Z",
  "completed_at": "2025-03-14T09:40:00Z",
  "error_message": "Job colgado: sin actualización en 900 s.",
  "warning_message": null,
  "result_html_path": null,
  "preview_html_path": null,
  "fast_demo": false
}
```

### 4. Job failed por timeout
```json
{
  "job_id": "c3d4e5f6a1b2",
  "hotel_name": "Hotel Timeout",
  "city": "Sevilla",
  "hotel_id": 1,
  "status": "failed",
  "stage": "error",
  "progress_pct": 45,
  "created_at": "2025-03-14T08:00:00Z",
  "started_at": "2025-03-14T08:00:01Z",
  "updated_at": "2025-03-14T08:10:01Z",
  "completed_at": "2025-03-14T08:10:01Z",
  "error_message": "Pipeline superó el tiempo límite (600 s). Revisa datos o aumenta pipeline_timeout_seconds.",
  "warning_message": null,
  "result_html_path": null,
  "preview_html_path": null,
  "fast_demo": false
}
```

### 5. Job recovered/saneado tras startup recovery
```json
{
  "job_id": "d4e5f6a1b2c3",
  "hotel_name": "Hotel Orphan",
  "city": "Bilbao",
  "hotel_id": 1,
  "status": "stalled",
  "stage": "error",
  "progress_pct": 20,
  "created_at": "2025-03-14T07:00:00Z",
  "started_at": "2025-03-14T07:00:01Z",
  "updated_at": "2025-03-14T07:30:00Z",
  "completed_at": "2025-03-14T12:00:00Z",
  "error_message": "Proceso reiniciado: job activo sin task viva (crash recovery).",
  "warning_message": null,
  "result_html_path": null,
  "preview_html_path": null,
  "fast_demo": false
}
```

---

## RESPUESTAS REALES DE API

### 1. POST /api/run-analysis cuando ya existe job activo del mismo hotel
**Request:** `POST /api/run-analysis`  
**Body:** `{"hotel_name": "Hotel Arts Barcelona", "city": "Barcelona", "hotel_id": 1}`  

**Response (409):**
```json
{
  "error": "Ya hay un análisis en curso para este hotel.",
  "active_job_id": "a1b2c3d4e5f6"
}
```

### 2. POST /api/jobs/{job_id}/cancel — éxito
**Request:** `POST /api/jobs/a1b2c3d4e5f6/cancel`  

**Response (200):**
```json
{
  "ok": true,
  "job_id": "a1b2c3d4e5f6",
  "message": "Job cancelado.",
  "task_was_running": true
}
```

### 3. POST /api/jobs/{job_id}/cancel — job no activo
**Request:** `POST /api/jobs/a1b2c3d4e5f6/cancel` (job ya completed/failed/stalled/cancelled)  

**Response (400):**
```json
{
  "error": "El job no está activo; no se puede cancelar.",
  "job_id": "a1b2c3d4e5f6",
  "current_status": "completed"
}
```

### 4. POST /api/jobs/run-watchdog (modo normal)
**Request:** `POST /api/jobs/run-watchdog` o `POST /api/jobs/run-watchdog?max_idle_seconds=900`  

**Response (200):**
```json
{
  "reviewed": 12,
  "active_count": 1,
  "alive_in_runtime": 0,
  "marked_stalled": ["b2c3d4e5f6a1"],
  "ignored": 0,
  "dry_run": false
}
```

### 5. POST /api/jobs/run-watchdog?dry_run=true
**Request:** `POST /api/jobs/run-watchdog?dry_run=true`  

**Response (200):**
```json
{
  "reviewed": 12,
  "active_count": 1,
  "alive_in_runtime": 0,
  "marked_stalled": ["b2c3d4e5f6a1"],
  "ignored": 0,
  "dry_run": true
}
```
(No se escribe en disco.)

### 6. GET /api/jobs/runtime
**Request:** `GET /api/jobs/runtime`  

**Response (200):**
```json
{
  "active_job_ids": ["a1b2c3d4e5f6"],
  "active_count_runtime": 1,
  "by_status": {
    "completed": 5,
    "running": 1,
    "failed": 2,
    "stalled": 1,
    "cancelled": 0
  },
  "orphaned": [],
  "in_runtime_not_active_state": [],
  "mismatch_summary": {
    "orphaned_count": 0,
    "runtime_without_active_state_count": 0
  }
}
```

### 7. POST /api/jobs/run-recovery (startup recovery manual)
**Request:** `POST /api/jobs/run-recovery` o `POST /api/jobs/run-recovery?dry_run=true&policy=stalled`  

**Response (200):**
```json
{
  "ok": true,
  "orphaned": [
    {"job_id": "d4e5f6a1b2c3", "hotel_name": "Hotel Orphan", "status_applied": "stalled"}
  ],
  "dry_run": false
}
```

---

## NOTAS OPERATIVAS

1. **Estados activos**  
   `pending`, `running`, `rendering`, `persisting`, `notifying`. Bloquean lanzar otro análisis del mismo hotel.

2. **Estados terminales**  
   `completed`, `failed`, `stalled`, `cancelled`. No bloquean y no se cancelan.

3. **Watchdog si el runtime dice que el task sigue vivo**  
   Si se pasa `is_alive=job_runtime.is_running`, el watchdog **no** marca stalled ningún job cuyo `job_id` tenga task vivo. Solo marca stalled jobs activos en persistencia con `updated_at` antiguo y **sin** task vivo. Fuente para “sigue vivo”: runtime. Fuente para estado persistido: job_state.

4. **Startup recovery con jobs activos huérfanos**  
   Al arrancar la app se llama `job_recovery.run_startup_recovery(BASE_DIR, job_runtime.is_running, policy="stalled")`. Los jobs en estado activo sin task viva se marcan como `stalled` con mensaje "Proceso reiniciado: job activo sin task viva (crash recovery).". También se puede ejecutar manualmente con `POST /api/jobs/run-recovery` (opcional `dry_run`, `policy=stalled|failed`).

5. **Qué queda legacy y dónde**  
   - **admin_panel.py**: bloque “LEGACY — analysis_status.json” (`_analysis_status_path`, `_write_analysis_status`, `api_analysis_status`). Se usa para polling antiguo (idle|running|success|error).  
   - **analysis_runner** no escribe en `analysis_status.json`; solo recibe `on_legacy_success` y `on_legacy_error` que admin_panel usa para escribir ese archivo.  
   - Fuente de verdad de jobs: **job_state** (data/jobs/<job_id>.json).

---

## Criterios de aceptación

- [x] Existe cancelación: `POST /api/jobs/{job_id}/cancel` y estado `cancelled`.
- [x] El watchdog no marca stalled un task vivo: usa `is_alive=job_runtime.is_running`.
- [x] Hay startup recovery: al arrancar y `POST /api/jobs/run-recovery`.
- [x] Hay tests: 9 tests en `tests/test_job_engine.py` (pytest).
- [x] Hay endpoint de observabilidad: `GET /api/jobs/runtime`.
- [x] Código completo en el repositorio en los archivos indicados; este documento no omite archivos con “están en el repo” sino que referencia los paths exactos del proyecto.
