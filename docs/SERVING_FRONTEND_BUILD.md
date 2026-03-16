# Servir el build de frontend-v0 desde FastAPI

Cuando quieras que la UI principal (frontend-v0) se sirva desde el mismo origen que el backend (por ejemplo en producción), sin levantar `npm run dev` por separado:

## Pasos

1. **Generar el build estático de frontend-v0**
   - En `frontend-v0/`: configurar Next.js para export estático si aún no está (por ejemplo `output: 'export'` en next.config o usar `next build` y servir la salida).
   - Ejecutar: `npm run build`.
   - La salida suele quedar en `frontend-v0/out` (export) o en `frontend-v0/.next` (standalone según config). Para servir estáticos necesitas una carpeta con `index.html` en la raíz.

2. **Copiar o enlazar la carpeta del build** a un directorio que FastAPI pueda servir (por ejemplo `frontend_v0_build` en la raíz del proyecto), de modo que ese directorio contenga `index.html` y los assets.

3. **En admin_panel.py**
   - Definir **después** de todas las rutas `/api/*` un montaje de archivos estáticos para `/`:
   - Importar: `from fastapi.staticfiles import StaticFiles`
   - Comprobar que existe el directorio del build.
   - Montar: `app.mount("/", StaticFiles(directory=_FRONTEND_BUILD, html=True), name="frontend")`
   - Importante: las rutas API deben estar registradas antes del `mount("/")`, para que `/api/*` sigan siendo manejadas por el backend y no por el estático.

4. **Rutas SPA**
   - Si frontend-v0 es una SPA (Next.js con client-side routing), el servidor debe devolver `index.html` para rutas no encontradas (fallback). `StaticFiles(..., html=True)` en FastAPI sirve `index.html` cuando no hay archivo estático, lo que suele bastar para una SPA.

5. **No romper la UI legacy**
   - Hasta no cambiar por completo, puedes dejar GET / como legacy (operator_console) y servir frontend-v0 en otra ruta (por ejemplo `/app`) o cambiar GET / al build cuando la migración esté lista.

Bloque de ejemplo (ya documentado en comentarios de admin_panel.py):

```python
from fastapi.staticfiles import StaticFiles
_FRONTEND_BUILD = os.path.join(BASE_DIR, "frontend_v0_build")
if os.path.isdir(_FRONTEND_BUILD):
    app.mount("/", StaticFiles(directory=_FRONTEND_BUILD, html=True), name="frontend")
```

Ajusta `_FRONTEND_BUILD` a la ruta real del build (por ejemplo `frontend-v0/out` si usas `output: 'export'`).
