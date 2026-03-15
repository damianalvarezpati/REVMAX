"""
RevMax — Generación y persistencia de artefactos HTML del informe.
Escribe preview por job en data/previews/<job_id>.html y reporte en data/reports/.
Devuelve siempre rutas relativas al base_dir del proyecto.
"""

import os
from datetime import datetime
from typing import Tuple


def preview_dir(base_dir: str) -> str:
    return os.path.join(base_dir, "data", "previews")


def reports_dir(base_dir: str) -> str:
    return os.path.join(base_dir, "data", "reports")


def rel_preview_path(job_id: str) -> str:
    """Ruta relativa del preview para un job (sin base_dir)."""
    return os.path.join("data", "previews", f"{job_id}.html").replace("\\", "/")


def rel_result_path(hotel_name: str, base_dir: str) -> str:
    """Ruta relativa del informe final (sin base_dir). Nombre incluye timestamp."""
    safe_name = hotel_name.replace(" ", "_").replace("/", "_")
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{safe_name}_{ts}.html"
    return os.path.join("data", "reports", filename).replace("\\", "/")


def write_preview(base_dir: str, job_id: str, html: str) -> str:
    """
    Escribe el HTML de vista previa en data/previews/<job_id>.html.
    Devuelve la ruta relativa al proyecto (ej: data/previews/abc123.html).
    """
    d = preview_dir(base_dir)
    os.makedirs(d, exist_ok=True)
    path_abs = os.path.join(d, f"{job_id}.html")
    with open(path_abs, "w", encoding="utf-8") as f:
        f.write(html)
        f.flush()
        os.fsync(f.fileno())
    return rel_preview_path(job_id)


def write_result_report(base_dir: str, hotel_name: str, html: str) -> str:
    """
    Escribe el informe final en data/reports/<hotel>_<timestamp>.html.
    Devuelve la ruta relativa al proyecto (ej: data/reports/Hotel_Ejemplo_20250314_1201.html).
    """
    d = reports_dir(base_dir)
    os.makedirs(d, exist_ok=True)
    rel = rel_result_path(hotel_name, base_dir)
    path_abs = os.path.join(base_dir, rel)
    with open(path_abs, "w", encoding="utf-8") as f:
        f.write(html)
        f.flush()
        os.fsync(f.fileno())
    return rel


def resolve_path(base_dir: str, relative_path: str) -> str:
    """Convierte ruta relativa a absoluta para servir o para DB si se guarda path."""
    if not relative_path or os.path.isabs(relative_path):
        return relative_path or ""
    return os.path.normpath(os.path.join(base_dir, relative_path))
