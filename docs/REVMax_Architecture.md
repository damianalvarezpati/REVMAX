# RevMax Architecture

## Overview

RevMax es un sistema de análisis automatizado para hoteles que ejecuta análisis complejos a través de un **Job Engine** robusto y un **Analysis Pipeline** basado en agentes.

La arquitectura está diseñada para ser:

- **Robusta ante fallos** — persistencia en disco, recovery al arranque
- **Auditable** — estado en `data/jobs/<job_id>.json`
- **Extensible** — capas separadas
- **Segura frente a concurrencia** — un análisis activo por hotel, registry con lock
- **Fácil de diagnosticar** — endpoint de observabilidad, watchdog con estadísticas

```
┌─────────────────────────────────────────────────────────────────┐
│  Dashboard / Frontend (HTML en admin_panel)                       │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Admin API (admin_panel.py) — FastAPI, puerto 8001               │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Job Engine (job_state, job_runtime, job_watchdog, etc.)         │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Analysis Runner (analysis_runner.py)                            │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Analysis Pipeline (orchestrator.py) → Agents + Data Sources    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### Admin API

**Archivo:** `admin_panel.py`

**Responsabilidades:**

- Exponer endpoints HTTP
- Lanzar análisis (crear job, registrar task, delegar en analysis_runner)
- Cancelar jobs
- Ejecutar watchdog
- Ejecutar recovery (manual y al startup)
- Servir previews y reportes
- Exponer observabilidad
- LEGACY: escribir `analysis_status.json` para polling antiguo (callbacks desde analysis_runner)

**Endpoints principales del Job Engine:**

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/run-analysis` | Lanza un análisis (hotel_name, city, etc.). 409 si ya hay job activo para ese hotel. |
| GET | `/api/job-status/{job_id}` | Estado persistente del job. |
| GET | `/api/jobs` | Lista de jobs recientes. |
| POST | `/api/jobs/run-watchdog` | Marca jobs colgados (stalled). Parámetros: `max_idle_seconds`, `dry_run`. |
| GET | `/api/jobs/runtime` | Snapshot de observabilidad (runtime vs persistencia). |
| POST | `/api/jobs/{job_id}/cancel` | Cancela un job activo. |
| POST | `/api/jobs/run-recovery` | Ejecuta recovery manual. Parámetros: `dry_run`, `policy=stalled|failed`. |

La API no ejecuta lógica de análisis directamente; solo coordina el Job Engine y delega en `analysis_runner.run_analysis_job()`.

---

### Job Engine

El Job Engine controla el ciclo de vida completo de los análisis.

**Archivos:**

| Archivo | Responsabilidad |
|---------|-----------------|
| `job_schema.py` | Estados, etapas, claves permitidas, transiciones de estado. |
| `job_state.py` | Persistencia en `data/jobs/<job_id>.json`. create_job, update_job, get_job, list_recent_jobs, touch_job, has_active_job_for_hotel. |
| `job_runtime.py` | Registro en memoria job_id → asyncio.Task. register, unregister, is_running, get_task, get_active_job_ids, cancel_task. Thread-safe con `threading.Lock`. |
| `job_watchdog.py` | Detección de jobs colgados (stalled). Consulta runtime para no marcar jobs con task viva. |
| `job_recovery.py` | Startup/crash recovery: jobs activos sin task viva → stalled o failed. |
| `job_observability.py` | Snapshot para diagnóstico: active_job_ids, by_status, orphaned, mismatch_summary. |
| `analysis_runner.py` | Ejecuta pipeline, actualiza estado del job, heartbeat, cancelación, artefactos, email. |

---

### Job Schema

**Archivo:** `job_schema.py`

**Estados posibles (ALLOWED_STATUSES):**

- `pending`, `running`, `rendering`, `persisting`, `notifying`, `completed`, `failed`, `stalled`, `cancelled`

**Estados activos (ACTIVE_STATUSES)** — bloquean lanzar otro análisis del mismo hotel:

- `pending`, `running`, `rendering`, `persisting`, `notifying`

**Estados terminales (TERMINAL_STATUSES):**

- `completed`, `failed`, `stalled`, `cancelled`

**Transiciones permitidas (ALLOWED_TRANSITIONS):**

```
pending    → running, cancelled
running    → rendering, failed, cancelled, stalled
rendering  → persisting, failed, cancelled
persisting → notifying, completed, failed
notifying  → completed, failed
completed  → (ninguna)
failed     → (ninguna)
cancelled  → (ninguna)
stalled    → (ninguna)
```

Cualquier otra transición (por ejemplo `running` → `completed`) lanza `ValueError` en `job_state.update_job()`.

---

### Job Persistence

**Archivo:** `job_state.py`

Cada job se guarda como **`data/jobs/<job_id>.json`** con escritura atómica (tmp + replace).

**Campos típicos:**

- `job_id`, `hotel_name`, `city`, `hotel_id`, `status`, `stage`, `progress_pct`
- `created_at`, `started_at`, `updated_at`, `completed_at`
- `error_message`, `warning_message`, `result_html_path`, `preview_html_path`, `fast_demo`

**Regla:** No modificar archivos bajo `data/jobs/` a mano; siempre usar `job_state.update_job()` o `job_state.touch_job()`.

---

### Runtime Registry

**Archivo:** `job_runtime.py`

Mantiene un diccionario en memoria: `job_id` → `asyncio.Task`. Todas las operaciones sobre el registry están protegidas por un **`threading.Lock`** para concurrencia segura.

**Funciones:**

- `register(job_id, task)` — async; se llama al arrancar el task.
- `unregister(job_id)` — se llama al terminar el task (éxito, fallo o cancelación).
- `is_running(job_id)` → bool
- `get_task(job_id)` → Task | None
- `get_active_job_ids()` → lista de job_id con task vivo
- `cancel_task(job_id)` → True si había task vivo y se canceló

---

### Analysis Runner

**Archivo:** `analysis_runner.py`

**Responsabilidades:**

- Poner el job en `running`, arrancar heartbeat (actualiza `updated_at` cada 20 s).
- Ejecutar el pipeline (orchestrator) con timeout.
- En caso de timeout o excepción: marcar `failed`; en caso de `CancelledError`: marcar `cancelled`.
- Fases posteriores: `rendering` → `persisting` → `notifying` → `completed`.
- Generar artefactos (preview, result report), persistir en DB, enviar email si aplica.
- Callbacks legacy: `on_legacy_success`, `on_legacy_error` (admin_panel escribe `analysis_status.json`).

**Flujo principal:** `run_analysis_job()` — no invocar el pipeline directamente; siempre a través de esta función.

---

### Analysis Pipeline

**Archivo:** `orchestrator.py`

Coordina los agentes. Flujo típico:

```
    Discovery
         │
         ▼
    Compset
         │
         ▼
    Parallel agents (Pricing, Demand, Reputation, Distribution)
         │
         ▼
    Consolidation
         │
         ▼
    Report generation
```

Los agentes viven en `agents/`. El scraper y otras fuentes de datos se usan desde el orquestador/agentes.

---

### Watchdog

**Archivo:** `job_watchdog.py`

**Función:** `mark_stale_jobs(base_dir, max_idle_seconds, stalled_message, *, is_alive=..., dry_run=False)`

Un job se marca como **stalled** solo cuando se cumplen **las tres** condiciones:

1. Estado en **ACTIVE_STATUSES**
2. **No** hay task viva en runtime (`is_alive(job_id)` es False)
3. Tiempo desde `updated_at` > `max_idle_seconds`

Si el task sigue vivo en runtime, el job **nunca** se marca stalled.

**Respuesta (ejemplo):**

- `reviewed` — total de jobs revisados
- `active_count` — jobs en estado activo
- `alive_in_runtime` — cuántos de esos tienen task viva (ignorados)
- `marked_stalled` — número de jobs marcados como stalled
- `marked_stalled_ids` — lista de job_id marcados
- `ignored` — igual que alive_in_runtime
- `dry_run` — si es true, no se escribe en disco

---

### Startup Recovery

**Archivo:** `job_recovery.py`

**Función:** `run_startup_recovery(base_dir, is_alive, *, policy="stalled"|"failed", message=..., dry_run=False)`

- Se ejecuta al arrancar el servidor (evento `startup` en admin_panel).
- Detecta jobs **activos en persistencia** sin **task viva** en runtime (huérfanos tras un crash).
- Les aplica la política: `stalled` o `failed`, con mensaje por defecto de crash recovery.
- También expuesto como **POST /api/jobs/run-recovery** para ejecución manual (`dry_run`, `policy`).

---

### Observability

**Archivo:** `job_observability.py`

**Función:** `get_runtime_snapshot(base_dir, get_active_job_ids_fn, is_running_fn, limit_recent=200)`

**Expuesta como:** **GET /api/jobs/runtime**

**Contenido del snapshot:**

- `active_job_ids` — job_ids con task vivo en runtime
- `active_count_runtime`
- `by_status` — conteos por estado (persistencia)
- `orphaned` — jobs activos en persistencia sin task viva
- `in_runtime_not_active_state` — job_ids en runtime cuyo job no existe o no está activo en persistencia
- `mismatch_summary` — `orphaned_count`, `runtime_without_active_state_count`

Sirve para diagnosticar desajustes entre runtime y persistencia.

---

## Job Lifecycle

```
  create_job() → pending
         │
         ▼
  run_analysis_job() empieza → running (heartbeat actualiza updated_at)
         │
         ├── timeout / excepción → failed
         ├── cancel_task() / CancelledError → cancelled
         ├── watchdog (idle + sin task viva) → stalled
         │
         ▼
  rendering → persisting → notifying → completed
```

---

## Concurrency Rules

- **Un solo análisis activo por hotel.** Antes de crear un job se llama a `job_state.has_active_job_for_hotel(base_dir, hotel_name)`. Si devuelve un `job_id`, la API responde **409** y no crea otro job.
- El **registry** en `job_runtime` es el único lugar que sabe si hay un task realmente en ejecución; la **persistencia** en `job_state` es la fuente de verdad del estado del job para consultas y recuperación.

---

## Design Principles

1. **Single source of truth para estado persistido:** `job_state` (archivos en `data/jobs/`). No depender de memoria para el estado del job.
2. **Separación de responsabilidades:** schema, persistencia, runtime, watchdog, recovery y observabilidad están en módulos distintos.
3. **Crash safety:** los jobs sobreviven a reinicios; el recovery al arranque sanea jobs huérfanos.
4. **Transiciones validadas:** `job_state.update_job()` rechaza transiciones no permitidas en `ALLOWED_TRANSITIONS`.
5. **Observabilidad:** GET `/api/jobs/runtime` y respuestas del watchdog permiten diagnosticar sin tocar disco a mano.

---

## Reglas importantes

- **No** modificar `data/jobs/*.json` directamente; usar **`job_state.update_job()`** (y `touch_job` para heartbeat).
- **No** lanzar el pipeline de análisis directamente; usar **`analysis_runner.run_analysis_job()`**.
- **No** cambiar `status` sin validar transición; `update_job(..., status=...)` ya aplica `ALLOWED_TRANSITIONS`.
- **No** marcar como stalled un job cuyo task sigue vivo; el watchdog recibe `is_alive=job_runtime.is_running`.
- Al añadir nuevos estados o transiciones, actualizar **`job_schema.py`** (ALLOWED_STATUSES, ACTIVE_STATUSES, ALLOWED_TRANSITIONS) y la lógica que dependa de ellos.
