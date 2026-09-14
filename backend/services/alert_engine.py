"""Create and maintain investigable alerts from newly computed risk scores."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

# Score bands are deliberately independent from the risk-engine labels so they
# can be tuned without changing risk calculation logic.
CRITICAL_THRESHOLD = 80.0
HIGH_THRESHOLD = 60.0
MODERATE_THRESHOLD = 40.0
HYSTERESIS_MARGIN = 5.0
DOWNGRADE_OBSERVATIONS_REQUIRED = 3
OPEN_STATUSES = {"new", "acknowledged", "active"}  # "active" supports legacy rows.


def severity_for_score(score: float) -> str | None:
    if score >= CRITICAL_THRESHOLD:
        return "critical"
    if score >= HIGH_THRESHOLD:
        return "high"
    if score >= MODERATE_THRESHOLD:
        return "moderate"
    return None


def _as_reason_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return [str(value)]


def _reasons(risk: dict[str, Any], classification: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "risk_reason_codes": _as_reason_list(risk.get("reasons")),
        "classification": (classification or {}).get("classification"),
        "classification_confidence": (classification or {}).get("confidence"),
    }


def evaluate_alert(db: Session, thermal_event_id: str) -> dict[str, Any] | None:
    """Synchronize an event's open alert after a risk recomputation.

    The caller owns transaction boundaries. Repeating an evaluation for an
    unchanged score updates neither the alert nor its hysteresis counter.
    """
    risk = db.execute(text("""
        SELECT risk_score, severity, reasons, created_at
        FROM risk_scores WHERE event_id = CAST(:event_id AS uuid)
        ORDER BY created_at DESC LIMIT 1
    """), {"event_id": thermal_event_id}).mappings().first()
    if risk is None:
        return None

    classification = db.execute(text("""
        SELECT classification, confidence, reasons
        FROM classifications WHERE event_id = CAST(:event_id AS uuid)
        ORDER BY created_at DESC LIMIT 1
    """), {"event_id": thermal_event_id}).mappings().first()
    score = float(risk["risk_score"])
    target = severity_for_score(score)
    alert = db.execute(text("""
        SELECT alert_id, severity, risk_score, reasons, status, created_at, updated_at
        FROM alerts WHERE event_id = CAST(:event_id AS uuid)
        ORDER BY created_at DESC LIMIT 1
    """), {"event_id": thermal_event_id}).mappings().first()

    if alert is None:
        if target is None:
            return None
        row = db.execute(text("""
            INSERT INTO alerts (event_id, severity, risk_score, reasons, status, created_at, updated_at)
            VALUES (CAST(:event_id AS uuid), :severity, :risk_score, CAST(:reasons AS jsonb), 'new', NOW(), NOW())
            RETURNING alert_id, severity, risk_score, reasons, status, created_at, updated_at
        """), {"event_id": thermal_event_id, "severity": target, "risk_score": score,
              "reasons": __import__("json").dumps(_reasons(risk, classification))}).mappings().one()
        return dict(row)

    # A manually closed incident is retained as history. A later qualifying
    # score opens a fresh incident only when the value has actually changed.
    if alert["status"] not in OPEN_STATUSES:
        if target is None or float(alert["risk_score"] or -1) == score:
            return dict(alert)
        return evaluate_alert_after_closed(db, thermal_event_id, score, target, risk, classification)

    current = str(alert["severity"])
    if float(alert["risk_score"] or -1) == score:
        return dict(alert)

    reasons = dict(alert["reasons"] or {})
    downgrade = target is None or _rank(target) < _rank(current)
    consecutive = int(reasons.get("below_threshold_observations", 0))
    should_hold = False
    if downgrade:
        threshold = {"critical": CRITICAL_THRESHOLD, "high": HIGH_THRESHOLD, "moderate": MODERATE_THRESHOLD}[current]
        should_hold = score > threshold - HYSTERESIS_MARGIN
        consecutive = 0 if should_hold else consecutive + 1
        if should_hold or consecutive < DOWNGRADE_OBSERVATIONS_REQUIRED:
            reasons["below_threshold_observations"] = consecutive
            db.execute(text("""
                UPDATE alerts SET risk_score=:risk_score, reasons=CAST(:reasons AS jsonb), updated_at=NOW()
                WHERE alert_id=CAST(:alert_id AS uuid)
            """), {"risk_score": score, "reasons": __import__("json").dumps(reasons), "alert_id": str(alert["alert_id"])})
            return dict(alert) | {"risk_score": score, "reasons": reasons}

    new_status = "resolved" if target is None else str(alert["status"])
    payload = _reasons(risk, classification)
    payload["below_threshold_observations"] = 0 if not downgrade else consecutive
    row = db.execute(text("""
        UPDATE alerts SET severity=:severity, risk_score=:risk_score, reasons=CAST(:reasons AS jsonb),
          status=:status, updated_at=NOW() WHERE alert_id=CAST(:alert_id AS uuid)
        RETURNING alert_id, severity, risk_score, reasons, status, created_at, updated_at
    """), {"severity": target or current, "risk_score": score, "reasons": __import__("json").dumps(payload),
          "status": new_status, "alert_id": str(alert["alert_id"])}).mappings().one()
    return dict(row)


def evaluate_alert_after_closed(db: Session, event_id: str, score: float, severity: str, risk: dict[str, Any], classification: dict[str, Any] | None) -> dict[str, Any]:
    row = db.execute(text("""
        INSERT INTO alerts (event_id, severity, risk_score, reasons, status, created_at, updated_at)
        VALUES (CAST(:event_id AS uuid), :severity, :score, CAST(:reasons AS jsonb), 'new', NOW(), NOW())
        RETURNING alert_id, severity, risk_score, reasons, status, created_at, updated_at
    """), {"event_id": event_id, "severity": severity, "score": score,
          "reasons": __import__("json").dumps(_reasons(risk, classification))}).mappings().one()
    return dict(row)


def _rank(severity: str) -> int:
    return {"moderate": 1, "high": 2, "critical": 3}.get(severity, 0)
