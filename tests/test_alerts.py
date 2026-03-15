"""
Tests unitarios del Alert Engine (Fase 4).
Ejecutar desde la raíz: pytest tests/test_alerts.py -v
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from alerts_engine import detect_alerts, build_alert_summary, count_alert_severity, ALERT_CONFIG


def _base_outputs(
    price_action="hold",
    demand_signal="medium",
    demand_score=55,
    parity_status="ok",
    visibility=0.8,
    gri_value=70,
    can_premium=False,
    price_perception="",
    your_rank=3,
    total=8,
):
    """Outputs mínimos de agentes para montar escenarios."""
    return {
        "pricing": {
            "recommendation": {"action": price_action},
            "market_context": {"your_position_rank": your_rank, "total_compset": total},
        },
        "demand": {
            "demand_index": {"signal": demand_signal, "score": demand_score},
        },
        "reputation": {
            "gri": {"value": gri_value, "can_command_premium": can_premium},
            "sentiment_analysis": {"price_perception": price_perception},
        },
        "distribution": {
            "visibility_score": visibility,
            "rate_parity": {"status": parity_status},
        },
    }


def _briefing_stub():
    return {"consolidated_price_action": "hold", "conflicts": []}


# 1) Parity violation → alerta crítica
def test_parity_violation_critical_alert():
    """Paridad violada debe generar alerta PARITY_VIOLATION con severity critical."""
    outputs = _base_outputs(parity_status="violation")
    conflicts = []
    briefing = _briefing_stub()
    alerts = detect_alerts(outputs, conflicts, briefing)
    types = [a["type"] for a in alerts]
    assert "PARITY_VIOLATION" in types
    parity_alert = next(a for a in alerts if a["type"] == "PARITY_VIOLATION")
    assert parity_alert["severity"] == "critical"
    assert parity_alert["source"] == "distribution"
    assert "message" in parity_alert


# 2) Visibility baja → warning
def test_low_visibility_warning():
    """Visibilidad por debajo del umbral debe generar LOW_VISIBILITY warning."""
    outputs = _base_outputs(visibility=0.35)
    conflicts = []
    briefing = _briefing_stub()
    alerts = detect_alerts(outputs, conflicts, briefing)
    types = [a["type"] for a in alerts]
    assert "LOW_VISIBILITY" in types
    vis_alert = next(a for a in alerts if a["type"] == "LOW_VISIBILITY")
    assert vis_alert["severity"] == "warning"
    assert vis_alert["source"] == "distribution"


# 3) Demand collapse → high
def test_demand_collapse_high():
    """Demand score muy bajo debe generar DEMAND_COLLAPSE con severity high."""
    outputs = _base_outputs(demand_score=28, demand_signal="low")
    conflicts = []
    briefing = _briefing_stub()
    alerts = detect_alerts(outputs, conflicts, briefing)
    types = [a["type"] for a in alerts]
    assert "DEMAND_COLLAPSE" in types
    demand_alert = next(a for a in alerts if a["type"] == "DEMAND_COLLAPSE")
    assert demand_alert["severity"] == "high"
    assert demand_alert["source"] == "demand"


# 4) Raise + demand baja → PRICE_TOO_HIGH_FOR_DEMAND
def test_price_too_high_for_demand():
    """Pricing recomienda raise y demanda baja debe generar PRICE_TOO_HIGH_FOR_DEMAND."""
    outputs = _base_outputs(price_action="raise", demand_signal="low")
    conflicts = []
    briefing = _briefing_stub()
    alerts = detect_alerts(outputs, conflicts, briefing)
    types = [a["type"] for a in alerts]
    assert "PRICE_TOO_HIGH_FOR_DEMAND" in types
    alert = next(a for a in alerts if a["type"] == "PRICE_TOO_HIGH_FOR_DEMAND")
    assert alert["severity"] == "high"
    assert alert["source"] == "pricing"


# 5) Reputación alta + posición baja en precios → STRONG_UNDERVALUE
def test_strong_undervalue():
    """GRI muy alto y posición débil en ranking debe generar STRONG_UNDERVALUE."""
    outputs = _base_outputs(gri_value=85, can_premium=True, your_rank=6, total=8)
    conflicts = []
    briefing = _briefing_stub()
    alerts = detect_alerts(outputs, conflicts, briefing)
    types = [a["type"] for a in alerts]
    assert "STRONG_UNDERVALUE" in types
    alert = next(a for a in alerts if a["type"] == "STRONG_UNDERVALUE")
    assert alert["severity"] == "warning"
    assert alert["source"] == "reputation"


def test_alert_summary_and_counts():
    """build_alert_summary y count_alert_severity deben ser coherentes."""
    outputs = _base_outputs(parity_status="violation", demand_score=30)
    alerts = detect_alerts(outputs, [], _briefing_stub())
    summary = build_alert_summary(alerts)
    assert "crítica" in summary.lower() or "critical" in summary.lower() or "alta" in summary.lower()
    assert count_alert_severity(alerts, "critical") >= 1
    assert count_alert_severity(alerts, "high") >= 0


def test_reputation_price_mismatch():
    """Reputación permite premium pero percepción 'caro' debe generar REPUTATION_PRICE_MISMATCH."""
    outputs = _base_outputs(can_premium=True, price_perception="Algunos huéspedes dicen que está caro")
    alerts = detect_alerts(outputs, [], _briefing_stub())
    types = [a["type"] for a in alerts]
    assert "REPUTATION_PRICE_MISMATCH" in types
    alert = next(a for a in alerts if a["type"] == "REPUTATION_PRICE_MISMATCH")
    assert alert["severity"] == "warning"
    assert alert["source"] == "reputation"


def test_alert_config_defined():
    """ALERT_CONFIG debe tener los umbrales esperados."""
    assert "visibility_low_threshold" in ALERT_CONFIG
    assert "demand_collapse_score_max" in ALERT_CONFIG
    assert "strong_reputation_gri_min" in ALERT_CONFIG
