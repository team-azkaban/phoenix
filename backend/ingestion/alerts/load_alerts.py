import json
import uuid

from sqlalchemy import text

from db.database import SessionLocal


ALERT_THRESHOLD = 50.0  # High-risk events only


def stable_uuid(event_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"phoenix-alert:{event_id}"))


def main():
    db = SessionLocal()

    try:
        events = db.execute(
            text(
                """
                SELECT
                    event_id,
                    risk_score,
                    severity,
                    risk_reasons
                FROM thermal_events
                WHERE risk_score IS NOT NULL
                ORDER BY event_id
                """
            )
        ).mappings().all()

        alerts = []

        for event in events:
            risk_score = float(event["risk_score"])

            # Only high/critical risk events become alerts.
            if risk_score < ALERT_THRESHOLD:
                continue

            event_id = str(event["event_id"])
            severity = event["severity"] or "high"

            risk_reasons = event["risk_reasons"]

            if risk_reasons is None:
                risk_reasons = []

            if isinstance(risk_reasons, str):
                try:
                    risk_reasons = json.loads(risk_reasons)
                except json.JSONDecodeError:
                    risk_reasons = [risk_reasons]

            reasons = {
                "alert_trigger": f"risk_score >= {ALERT_THRESHOLD}",
                "risk_score": risk_score,
                "risk_reasons": risk_reasons,
            }

            alerts.append(
                {
                    "alert_id": stable_uuid(event_id),
                    "event_id": event_id,
                    "severity": severity,
                    "risk_score": risk_score,
                    "reasons": json.dumps(reasons),
                    "status": "active",
                }
            )

        print(f"Risk-scored events: {len(events)}")
        print(f"Alerts prepared: {len(alerts)}")

        if alerts:
            db.execute(
                text(
                    """
                    INSERT INTO alerts (
                        alert_id,
                        event_id,
                        severity,
                        risk_score,
                        reasons,
                        status
                    )
                    SELECT
                        x.alert_id::uuid,
                        x.event_id::uuid,
                        x.severity,
                        x.risk_score,
                        x.reasons::jsonb,
                        x.status
                    FROM jsonb_to_recordset(
                        CAST(:payload AS jsonb)
                    ) AS x(
                        alert_id text,
                        event_id text,
                        severity text,
                        risk_score double precision,
                        reasons text,
                        status text
                    )
                    ON CONFLICT (alert_id)
                    DO UPDATE SET
                        severity = EXCLUDED.severity,
                        risk_score = EXCLUDED.risk_score,
                        reasons = EXCLUDED.reasons,
                        status = EXCLUDED.status
                    """
                ),
                {
                    "payload": json.dumps(alerts)
                },
            )

        # Synchronize the alert state back onto thermal_events.
        db.execute(
            text(
                """
                UPDATE thermal_events
                SET
                    alert_status = CASE
                        WHEN risk_score >= :threshold
                            THEN 'active'
                        ELSE 'none'
                    END,
                    alert_reasons = CASE
                        WHEN risk_score >= :threshold
                            THEN COALESCE(risk_reasons, '[]'::jsonb)
                        ELSE '[]'::jsonb
                    END,
                    updated_at = NOW()
                """
            ),
            {"threshold": ALERT_THRESHOLD},
        )

        db.commit()

        alert_count = db.execute(
            text("SELECT COUNT(*) FROM alerts")
        ).scalar_one()

        active_event_alerts = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM thermal_events
                WHERE alert_status = 'active'
                """
            )
        ).scalar_one()

        high_risk_events = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM thermal_events
                WHERE risk_score >= :threshold
                """
            ),
            {"threshold": ALERT_THRESHOLD},
        ).scalar_one()

        print(f"Alerts table rows: {alert_count}")
        print(f"High-risk events: {high_risk_events}")
        print(f"Events marked active: {active_event_alerts}")

        if alert_count != high_risk_events:
            raise RuntimeError(
                "FAIL: alerts count does not match high-risk event count"
            )

        if active_event_alerts != high_risk_events:
            raise RuntimeError(
                "FAIL: thermal_events alert status does not match"
            )

        print("PASS: alerts populated and synchronized.")

    finally:
        db.close()


if __name__ == "__main__":
    main()