"""
RevMax — Utilidades para clasificación y mensajes de error.
Origen del error desde traceback (agentes, orquestador, mailer, scraper).
"""

import traceback


def get_error_source(exc: BaseException) -> str:
    """
    Devuelve una descripción legible del origen del error a partir del traceback.
    Usado por analysis_runner y admin_panel para reportes de fallo.
    """
    tb = exc.__traceback__
    if tb is None:
        return "desconocido"
    try:
        for filename, lineno, _name, _line in reversed(traceback.extract_tb(tb)):
            if "site-packages" in filename or "lib/python" in filename:
                continue
            if "agents" in filename and "agent_01" in filename:
                return f"Agente Discovery (agents/agent_01_discovery.py, línea {lineno})"
            if "agents" in filename and "agent_02" in filename:
                return f"Agente Compset (agents/agent_02_compset.py, línea {lineno})"
            if "agents" in filename and "agent_03" in filename:
                return f"Agente Pricing (agents/agent_03_pricing.py, línea {lineno})"
            if "agents" in filename and "agent_04" in filename:
                return f"Agente Demand (agents/agent_04_demand.py, línea {lineno})"
            if "agents" in filename and "agent_05" in filename:
                return f"Agente Reputación (agents/agent_05_reputation.py, línea {lineno})"
            if "agents" in filename and "agent_06" in filename:
                return f"Agente Distribución (agents/agent_06_distribution.py, línea {lineno})"
            if "agents" in filename and "agent_07" in filename:
                return f"Agente Informe (agents/agent_07_report.py, línea {lineno})"
            if "orchestrator" in filename:
                return f"Orquestador (orchestrator.py, línea {lineno})"
            if "report_mailer" in filename or ("mailer" in filename and "report" in filename):
                return f"Email (mailer/, línea {lineno})"
            if "scraper" in filename or "booking_scraper" in filename or "rate_shopper" in filename:
                return f"Scraping (scraper/, línea {lineno})"
        return "pipeline de análisis"
    except Exception:
        return "desconocido"
