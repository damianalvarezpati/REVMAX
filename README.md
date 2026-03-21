# RevMax — Revenue Intelligence for Hotels

---

## UI principal: frontend-v0 (doble clic)

**FRONTEND PRINCIPAL OFICIAL:** `frontend-v0/` (Next.js, export v0).  
La pantalla Analysis está conectada al backend real (run-analysis, job-status).

**Arrancar todo con doble clic (macOS):**

1. Dar permisos de ejecución **una vez** (en Terminal, dentro de la carpeta del proyecto):
   ```bash
   chmod +x start_revmax.command stop_revmax.command
   ```
2. Doble clic en **`start_revmax.command`**: arranca backend (puerto 8001) + frontend-v0 (puerto 3000) y abre el navegador en **http://localhost:3000**.
3. Para parar: doble clic en **`stop_revmax.command`** o, en la ventana que abrió el launcher, pulsar **Enter** (si configuraste el launcher para que Enter detenga los servicios).

**Puertos:** Backend = **8001**. Frontend principal = **3000**.

**Requisitos:** Python 3 con dependencias del proyecto (`.venv` recomendado), Node.js/npm para frontend-v0. El launcher activa `.venv` y, si hace falta, ejecuta `npm install` en frontend-v0 la primera vez.

Otras UIs (operator_console, frontend/) son **legacy/fallback**; ver **FRONTENDS.md**.

---

## RevMax Daily — Informe por email

Recibe cada mañana un informe por email con:
- Tu posición en Booking vs la competencia
- Alertas de promociones de otros hoteles
- Precio recomendado por tipo de habitación
- Análisis de demanda del mercado
- Recomendaciones concretas generadas por IA

---

## Instalación paso a paso (15 minutos)

### Paso 1 — Instalar Python

1. Abre el navegador y ve a: https://www.python.org/downloads/
2. Haz clic en el botón amarillo grande "Download Python 3.x.x"
3. Abre el archivo descargado y sigue el instalador
4. **IMPORTANTE en Windows:** marca la casilla "Add Python to PATH" antes de instalar

Para verificar que se instaló bien, abre Terminal (Mac) o CMD (Windows) y escribe:
```
python --version
```
Debes ver algo como: `Python 3.11.x`

---

### Paso 2 — Descargar RevMax

Descarga la carpeta `revmax` en tu escritorio.

---

### Paso 3 — Abrir Terminal en la carpeta de RevMax

**En Mac:**
1. Abre la carpeta `revmax` en Finder
2. Haz clic derecho → "Nuevo Terminal en la carpeta"

**En Windows:**
1. Abre la carpeta `revmax` en el Explorador
2. Haz clic en la barra de dirección, escribe `cmd` y pulsa Enter

---

### Paso 4 — Instalar dependencias

En la ventana de Terminal/CMD, copia y pega este comando:

```
pip install -r requirements.txt
```

Espera a que termine (puede tardar 1-2 minutos). Verás texto verde.

---

### Paso 5 — Configurar tu hotel

Ejecuta el asistente de configuración:

```
python setup_wizard.py
```

El asistente te hará preguntas simples:
- Nombre de tu hotel (como aparece en Booking)
- Tu ciudad
- Tipos de habitación y precios
- Nombres de tus competidores principales
- Tu email de Gmail para enviar informes
- Tu clave de API de Claude (ver más abajo)

**Cómo conseguir la clave de API de Claude (gratis):**
1. Ve a https://console.anthropic.com
2. Crea una cuenta gratuita
3. Ve a "API Keys" → "Create Key"
4. Copia la clave (empieza por `sk-ant-...`)

**Contraseña de aplicación de Gmail:**
1. Ve a myaccount.google.com
2. Seguridad → Verificación en 2 pasos (actívala si no la tienes)
3. Busca "Contraseñas de aplicaciones"
4. Elige "Correo" + "Mac" o "Windows"
5. Google te da una contraseña de 16 letras — cópiala

---

### Paso 6 — Probar el sistema

```
python run_revmax.py --preview
```

Esto genera el informe sin enviarlo. Se guardará en `data/report_preview.html`.
Abre ese archivo en tu navegador para ver cómo quedará el email.

Si todo se ve bien, prueba el envío real:

```
python run_revmax.py
```

Debes recibir el email en unos minutos.

---

### Paso 7 — Activar el informe diario automático

Para que el informe llegue solo cada día a la hora configurada:

```
python scheduler.py
```

Deja esa ventana de Terminal abierta en segundo plano.
El informe llegará todos los días a la hora que configuraste (por defecto: 07:30).

---

## Solución de problemas comunes

**"python: command not found"**
→ Reinstala Python y asegúrate de marcar "Add to PATH"

**"No module named 'requests'"**
→ Ejecuta de nuevo: `pip install -r requirements.txt`

**"No se encontraron hoteles"**
→ Booking puede bloquear temporalmente el scraper. Espera 30 minutos e intenta de nuevo.
   Si persiste, el scraper puede necesitar actualización (los sitios web cambian).

**El email no llega**
→ Revisa que la contraseña de aplicación de Gmail es correcta (sin espacios)
→ Verifica la carpeta de spam

---

## Archivos del proyecto

```
revmax/
  run_revmax.py          ← Punto de entrada principal
  setup_wizard.py        ← Configuración inicial
  scheduler.py           ← Envío automático diario
  config.json            ← Tu configuración (se crea con el wizard)
  requirements.txt       ← Dependencias Python
  scraper/
    booking_scraper.py   ← Obtiene precios de Booking.com
  analyzer/
    market_analyzer.py   ← Compara y genera insights
  mailer/
    report_mailer.py     ← Genera email HTML y lo envía
  data/
    prices_latest.json   ← Últimos datos de precios
    report_preview.html  ← Preview del último informe
```

---

## Personalización

Para cambiar cualquier configuración, edita `config.json` con cualquier editor de texto (Bloc de notas en Windows, TextEdit en Mac).

Los campos más útiles:
- `schedule_time`: hora de envío (formato "HH:MM")
- `base_prices`: tus precios actuales por tipo de habitación
- `competitor_names`: añade o quita competidores
- `min_price` / `max_price`: límites absolutos de precio

---

## Documentación (RevMax Intelligence / Dojo)

- **[docs/DOJO_ROLE_AND_PRINCIPLES.md](docs/DOJO_ROLE_AND_PRINCIPLES.md)** — Rol del Dojo como sensei del conocimiento (normativo para diseño).
- [docs/DOJO_DEFINITION_OF_DONE.md](docs/DOJO_DEFINITION_OF_DONE.md) — Definition of Done operativo.
- [docs/DOJO_AUDIT_VS_CHARTER.md](docs/DOJO_AUDIT_VS_CHARTER.md) — Auditoría del Dojo vs charter (estado real).
- [docs/KNOWLEDGE_INPUTS_DOJO.md](docs/KNOWLEDGE_INPUTS_DOJO.md) · [docs/KNOWLEDGE_REFRESH.md](docs/KNOWLEDGE_REFRESH.md) · [docs/KNOWLEDGE_BALANCING.md](docs/KNOWLEDGE_BALANCING.md) · [docs/DOJO_VALIDATION_DEBT.md](docs/DOJO_VALIDATION_DEBT.md)

---

*RevMax Daily — Versión 1.0*
