"""
RevMax — Persistence / Intelligence Memory Layer (Fase 8)
=========================================================
Conserva histórico estructurado de hallazgos por hotel,
compara corrida actual con la anterior y produce memory_summary.
Persistencia simple en JSON por carpeta data/intelligence_history/<hotel_slug>/.
"""

import json
import os
import re
from datetime import datetime
from typing import Optional

STATUS_ORDER = {"alert": 0, "needs_attention": 1, "stable": 2, "strong": 3}
ATTENTION_TREND_VALUES = ("worsening", "improving", "stable")


def _hotel_slug(hotel_name: str) -> str:
    """Nombre de hotel a slug seguro para carpetas."""
    if not hotel_name or not str(hotel_name).strip():
        return "unknown"
    s = str(hotel_name).strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "_", s)
    return s[:64] if s else "unknown"


def _history_dir(base_path: str, hotel_slug: str) -> str:
    """Ruta a la carpeta de histórico del hotel."""
    return os.path.join(base_path, "data", "intelligence_history", hotel_slug)


def _build_short_summary(briefing: dict) -> str:
    """Resumen ejecutivo breve derivado por código."""
    strategy = briefing.get("strategy_label", "BALANCED")
    status = briefing.get("derived_overall_status", "stable")
    action = briefing.get("consolidated_price_action", "hold")
    critical = briefing.get("alert_critical_count", 0)
    high = briefing.get("alert_high_count", 0)
    notif_count = len(briefing.get("top_notifications", []))
    parts = [f"Strategy {strategy}, status {status}, action {action.upper()}."]
    if critical or high:
        parts.append(f" Alerts: {critical} critical, {high} high.")
    if notif_count:
        parts.append(f" {notif_count} top notification(s).")
    return "".join(parts).strip()


def _snapshot_from_briefing(briefing: dict, hotel_name: str) -> dict:
    """Construye el dict del snapshot a persistir (solo inteligencia útil)."""
    alerts = briefing.get("alerts", [])
    market_signals = briefing.get("market_signals", [])
    recommended_actions = briefing.get("recommended_actions", [])
    top_notifications = briefing.get("top_notifications", [])

    alert_types = sorted({a.get("type") for a in alerts if a.get("type")})
    market_signal_types = sorted({s.get("type") for s in market_signals if s.get("type")})
    recommended_action_types = sorted({a.get("type") for a in recommended_actions if a.get("type")})
    top_notification_types = sorted({n.get("type") for n in top_notifications if n.get("type")})

    return {
        "hotel_name": hotel_name,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "strategy_label": briefing.get("strategy_label", "BALANCED"),
        "derived_overall_status": briefing.get("derived_overall_status", "stable"),
        "consolidated_price_action": briefing.get("consolidated_price_action", "hold"),
        "alert_types": alert_types,
        "high_alert_count": briefing.get("alert_high_count", 0),
        "critical_alert_count": briefing.get("alert_critical_count", 0),
        "market_signal_types": market_signal_types,
        "recommended_action_types": recommended_action_types,
        "top_notification_types": top_notification_types,
        "short_summary": _build_short_summary(briefing),
    }


def save_snapshot(briefing: dict, hotel_name: str, base_path: Optional[str] = None) -> str:
    """
    Persiste snapshot de la corrida actual en data/intelligence_history/<hotel_slug>/.
    Nombre del archivo: snapshot_<YYYY-MM-DDTHHMMSS>Z.json
    Devuelve la ruta absoluta del archivo guardado.
    """
    base = base_path or os.path.dirname(os.path.abspath(__file__))
    slug = _hotel_slug(hotel_name)
    dir_path = _history_dir(base, slug)
    os.makedirs(dir_path, exist_ok=True)
    snapshot = _snapshot_from_briefing(briefing, hotel_name)
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H%M%S") + "Z"
    filename = f"snapshot_{ts.replace(':', '')}.json"
    file_path = os.path.join(dir_path, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    return os.path.abspath(file_path)


def load_previous_snapshot(hotel_name: str, base_path: Optional[str] = None) -> Optional[dict]:
    """
    Carga el snapshot más reciente del hotel (por timestamp en nombre de archivo).
    Devuelve None si no hay ninguno.
    """
    base = base_path or os.path.dirname(os.path.abspath(__file__))
    slug = _hotel_slug(hotel_name)
    dir_path = _history_dir(base, slug)
    if not os.path.isdir(dir_path):
        return None
    candidates = [f for f in os.listdir(dir_path) if f.startswith("snapshot_") and f.endswith(".json")]
    if not candidates:
        return None
    candidates.sort(reverse=True)
    latest = candidates[0]
    path = os.path.join(dir_path, latest)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def compare_with_previous(current_briefing: dict, previous_snapshot: Optional[dict]) -> dict:
    """
    Compara la corrida actual (briefing) con el snapshot previo.
    Devuelve repeated_alerts, new_alerts, resolved_alerts, repeated_notifications,
    strategy_changed, overall_status_changed, action_shift, attention_trend.
    """
    result = {
        "repeated_alerts": [],
        "new_alerts": [],
        "resolved_alerts": [],
        "repeated_notifications": [],
        "strategy_changed": False,
        "overall_status_changed": False,
        "action_shift": None,
        "attention_trend": "stable",
    }

    if not previous_snapshot:
        return result

    curr_alerts = sorted({a.get("type") for a in current_briefing.get("alerts", []) if a.get("type")})
    prev_alerts = previous_snapshot.get("alert_types", [])
    if isinstance(prev_alerts, list):
        prev_alerts = sorted(prev_alerts)
    else:
        prev_alerts = []

    result["repeated_alerts"] = sorted(set(curr_alerts) & set(prev_alerts))
    result["new_alerts"] = sorted(set(curr_alerts) - set(prev_alerts))
    result["resolved_alerts"] = sorted(set(prev_alerts) - set(curr_alerts))

    curr_notif = sorted({n.get("type") for n in current_briefing.get("top_notifications", []) if n.get("type")})
    prev_notif = previous_snapshot.get("top_notification_types", [])
    if isinstance(prev_notif, list):
        prev_notif = sorted(prev_notif)
    else:
        prev_notif = []
    result["repeated_notifications"] = sorted(set(curr_notif) & set(prev_notif))

    curr_strategy = current_briefing.get("strategy_label", "BALANCED")
    prev_strategy = previous_snapshot.get("strategy_label", "BALANCED")
    result["strategy_changed"] = curr_strategy != prev_strategy

    curr_status = current_briefing.get("derived_overall_status", "stable")
    prev_status = previous_snapshot.get("derived_overall_status", "stable")
    result["overall_status_changed"] = curr_status != prev_status

    curr_action = current_briefing.get("consolidated_price_action", "hold")
    prev_action = previous_snapshot.get("consolidated_price_action", "hold")
    if curr_action != prev_action:
        result["action_shift"] = f"{prev_action} -> {curr_action}"

    prev_rank = STATUS_ORDER.get(prev_status, 1)
    curr_rank = STATUS_ORDER.get(curr_status, 1)
    prev_alert_count = previous_snapshot.get("critical_alert_count", 0) + previous_snapshot.get("high_alert_count", 0)
    curr_alert_count = current_briefing.get("alert_critical_count", 0) + current_briefing.get("alert_high_count", 0)

    if curr_rank < prev_rank or curr_alert_count > prev_alert_count:
        result["attention_trend"] = "worsening"
    elif curr_rank > prev_rank or curr_alert_count < prev_alert_count:
        result["attention_trend"] = "improving"
    else:
        result["attention_trend"] = "stable"

    return result


def _build_memory_summary(
    previous_found: bool,
    comparison: dict,
    hotel_name: str,
) -> str:
    """Genera memory_summary legible para humanos y report."""
    if not previous_found:
        return f"No hay corrida previa para {hotel_name}; esta es la primera vez que se guarda memoria."

    lines = []
    if comparison.get("repeated_alerts"):
        lines.append(f"Persisten las alertas: {', '.join(comparison['repeated_alerts'])}.")
    if comparison.get("new_alerts"):
        lines.append(f"Nuevas alertas: {', '.join(comparison['new_alerts'])}.")
    if comparison.get("resolved_alerts"):
        lines.append(f"Alertas resueltas desde la corrida anterior: {', '.join(comparison['resolved_alerts'])}.")
    if comparison.get("strategy_changed"):
        lines.append("La estrategia ha cambiado respecto a la corrida anterior.")
    if comparison.get("overall_status_changed"):
        lines.append("El estado global ha cambiado respecto a la corrida anterior.")
    if comparison.get("action_shift"):
        lines.append(f"Cambio de acción consolidada: {comparison['action_shift']}.")
    trend = comparison.get("attention_trend", "stable")
    if trend == "worsening":
        lines.append("Tendencia de atención: empeoramiento (más alertas o estado más grave).")
    elif trend == "improving":
        lines.append("Tendencia de atención: mejora (menos alertas o estado mejor).")
    else:
        lines.append("Tendencia de atención: estable.")

    return " ".join(lines) if lines else "Sin cambios destacados respecto a la corrida anterior."


def build_memory_bundle(briefing: dict, hotel_name: str, base_path: Optional[str] = None) -> dict:
    """
    Carga el snapshot previo (si existe), compara con la corrida actual, guarda snapshot actual.
    Devuelve dict con memory_snapshot_path, previous_snapshot_found, repeated_alerts,
    new_alerts, resolved_alerts, repeated_notifications, strategy_changed,
    overall_status_changed, action_shift, attention_trend, memory_summary.
    """
    base = base_path or os.path.dirname(os.path.abspath(__file__))
    previous = load_previous_snapshot(hotel_name, base)

    if previous:
        comparison = compare_with_previous(briefing, previous)
    else:
        comparison = compare_with_previous(briefing, None)

    snapshot_path = save_snapshot(briefing, hotel_name, base)
    memory_summary = _build_memory_summary(previous is not None, comparison, hotel_name)

    return {
        "memory_snapshot_path": snapshot_path,
        "previous_snapshot_found": previous is not None,
        "repeated_alerts": comparison.get("repeated_alerts", []),
        "new_alerts": comparison.get("new_alerts", []),
        "resolved_alerts": comparison.get("resolved_alerts", []),
        "repeated_notifications": comparison.get("repeated_notifications", []),
        "strategy_changed": comparison.get("strategy_changed", False),
        "overall_status_changed": comparison.get("overall_status_changed", False),
        "action_shift": comparison.get("action_shift"),
        "attention_trend": comparison.get("attention_trend", "stable"),
        "memory_summary": memory_summary,
    }
