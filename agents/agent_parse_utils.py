"""
Utilidades compartidas para parse robusto de respuestas LLM en agentes 1-6.
Logging de fallos de parse sin lanzar excepciones.
"""

import os
import re
import json
from datetime import datetime
from typing import Optional, Tuple

MAX_RAW_LOG_CHARS = 2000
_DEBUG_LOG_DIR = "data"
_DEBUG_LOG_NAME = "agent_parse_failures.log"


def _log_path() -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, _DEBUG_LOG_DIR, _DEBUG_LOG_NAME)


def log_agent_parse_failure(
    agent_name: str,
    prompt_len: int,
    response_len: int,
    raw_preview: str,
    parse_error: str,
) -> None:
    try:
        path = _log_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(
                f"\n[{datetime.utcnow().isoformat()}Z] agent={agent_name} "
                f"prompt_len={prompt_len} response_len={response_len}\n"
                f"parse_error: {parse_error}\n"
                f"raw_preview:\n{raw_preview[:MAX_RAW_LOG_CHARS]}\n"
            )
            f.flush()
    except Exception:
        pass


def parse_json_response(raw: str) -> Tuple[Optional[dict], Optional[str]]:
    """
    Intenta parsear JSON desde la respuesta cruda.
    1) json.loads(raw)
    2) extraer bloque con regex r'\\{[\\s\\S]*\\}' y json.loads
    Devuelve (dict, None) si hay éxito, (None, parse_error_str) si falla.
    """
    raw = (raw or "").strip()
    err = "unknown"
    try:
        out = json.loads(raw)
        if isinstance(out, dict):
            return out, None
        err = "JSON root is not a dict"
    except json.JSONDecodeError as e:
        err = str(e)
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        try:
            out = json.loads(match.group(0))
            if isinstance(out, dict):
                return out, None
        except json.JSONDecodeError as e2:
            err = f"{err}; regex_block: {e2}"
        except Exception as e2:
            err = f"{err}; regex_block: {e2}"
    return None, err
