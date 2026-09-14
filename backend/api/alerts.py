"""Incident-focused Alerts API."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.database import get_db

router = APIRouter(prefix="/alerts", tags=["alerts"])
AlertStatus = Literal["acknowledged", "resolved", "false_positive"]


class AlertStatusUpdate(BaseModel):
    status: AlertStatus


def iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


def probability_breakdown(reasons: Any, label: str | None, confidence: float | None) -> dict[str, float]:
    if isinstance(reasons, dict):
        candidates = reasons.get("probabilities", reasons.get("probability_breakdown", reasons))
        if isinstance(candidates, dict):
            numeric = {str(k): float(v) for k, v in candidates.items() if isinstance(v, (int, float))}
            if numeric:
                return numeric
    if label and confidence is not None:
        return {label: float(confidence), "unknown": max(0.0, 1 - float(confidence))}
    return {"unknown": 1.0}


def detail_payload(db: Session, alert_id: str) -> dict[str, Any]:
    row = db.execute(text("""
        SELECT a.alert_id, a.event_id, a.severity, a.risk_score, a.reasons, a.status, a.created_at, a.updated_at,
          te.first_seen, te.last_seen, te.current_frp, te.baseline_frp, te.baseline_deviation,
          te.population_exposed, te.emissions_estimate, te.wind_direction, te.facility_distance_m,
          te.latitude AS event_latitude, te.longitude AS event_longitude,
          f.facility_id, f.name AS facility_name, f.facility_type, f.latitude AS facility_latitude, f.longitude AS facility_longitude,
          c.classification, c.confidence, c.reasons AS classification_reasons,
          e.emissions_estimate AS emission_record_estimate, si.image_url
        FROM alerts a JOIN thermal_events te ON te.event_id = a.event_id
        LEFT JOIN facilities f ON f.facility_id = te.facility_id
        LEFT JOIN LATERAL (SELECT classification, confidence, reasons FROM classifications WHERE event_id=te.event_id ORDER BY created_at DESC LIMIT 1) c ON TRUE
        LEFT JOIN LATERAL (SELECT emissions_estimate FROM emissions WHERE event_id=te.event_id ORDER BY created_at DESC LIMIT 1) e ON TRUE
        LEFT JOIN LATERAL (SELECT image_url FROM satellite_images WHERE event_id=te.event_id ORDER BY image_timestamp DESC NULLS LAST, created_at DESC LIMIT 1) si ON TRUE
        WHERE a.alert_id=CAST(:alert_id AS uuid)
    """), {"alert_id": alert_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    points = list(reversed(db.execute(text("""
        SELECT o.timestamp, o.frp FROM event_observations eo JOIN thermal_observations o ON o.observation_id=eo.observation_id
        WHERE eo.event_id=CAST(:event_id AS uuid) ORDER BY o.timestamp DESC LIMIT 5
    """), {"event_id": str(row["event_id"])}).mappings().all()))
    frp_points = [{"timestamp": iso(p["timestamp"]), "frp": p["frp"], "current": False} for p in points]
    if frp_points: frp_points[-1]["current"] = True
    elif row["current_frp"] is not None: frp_points = [{"timestamp": iso(row["last_seen"]), "frp": row["current_frp"], "current": True}]
    baseline = row["baseline_frp"]
    ratio = float(row["current_frp"]) / float(baseline) if row["current_frp"] is not None and baseline not in (None, 0) else None
    return {"id": str(row["alert_id"]), "event_id": str(row["event_id"]), "severity": row["severity"], "risk_score": row["risk_score"], "status": row["status"], "reasons": row["reasons"] or {}, "created_at": iso(row["created_at"]), "updated_at": iso(row["updated_at"]),
      "facility": {"id": str(row["facility_id"]) if row["facility_id"] else None, "name": row["facility_name"] or "Unassigned thermal source", "type": row["facility_type"], "location": {"latitude": row["facility_latitude"] or row["event_latitude"], "longitude": row["facility_longitude"] or row["event_longitude"]}},
      "classification": {"label": row["classification"] or "unknown", "confidence": row["confidence"], "probabilities": probability_breakdown(row["classification_reasons"], row["classification"], row["confidence"])},
      "frp_series": {"baseline": baseline, "points": frp_points},
      "risk_breakdown": {"population_exposed": row["population_exposed"], "estimated_emissions": row["emission_record_estimate"] or row["emissions_estimate"], "frp_deviation_ratio": ratio, "wind_direction": row["wind_direction"], "hazardous_context": bool(row["facility_type"] or row["facility_distance_m"] is not None)},
      "satellite_image_url": row["image_url"], "timeline": [{"at": iso(row["created_at"]), "status": "new", "label": "Alert created"}, {"at": iso(row["updated_at"]), "status": row["status"], "label": f"Status: {row['status']}"}]}


@router.get("")
def list_alerts(severity: str | None = None, status: str | None = None, facility_id: str | None = None, start: datetime | None = None, end: datetime | None = None, limit: Annotated[int, Query(ge=1, le=100)] = 50, offset: Annotated[int, Query(ge=0)] = 0, db: Session = Depends(get_db)):
    filters = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if severity:
        filters.append("a.severity = :severity")
        params["severity"] = severity
    if status:
        filters.append("a.status = :status")
        params["status"] = status
    if facility_id:
        filters.append("te.facility_id = CAST(:facility_id AS uuid)")
        params["facility_id"] = facility_id
    if start:
        filters.append("a.created_at >= :start")
        params["start"] = start
    if end:
        filters.append("a.created_at <= :end")
        params["end"] = end
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = db.execute(text(f"""SELECT a.alert_id, a.event_id, a.severity, a.risk_score, a.status, a.created_at, f.name AS facility_name, COALESCE(c.classification, te.classification, 'unknown') AS classification FROM alerts a JOIN thermal_events te ON te.event_id=a.event_id LEFT JOIN facilities f ON f.facility_id=te.facility_id LEFT JOIN LATERAL (SELECT classification FROM classifications WHERE event_id=te.event_id ORDER BY created_at DESC LIMIT 1) c ON TRUE {where} ORDER BY a.risk_score DESC NULLS LAST, a.created_at DESC LIMIT :limit OFFSET :offset"""), params).mappings().all()
    return {"count": len(rows), "alerts": [{"id": str(r["alert_id"]), "event_id": str(r["event_id"]), "facility_name": r["facility_name"] or "Unassigned thermal source", "classification": r["classification"], "severity": r["severity"], "risk_score": r["risk_score"], "status": r["status"], "created_at": iso(r["created_at"])} for r in rows]}


@router.get("/{alert_id}")
def get_alert(alert_id: str, db: Session = Depends(get_db)): return detail_payload(db, alert_id)


@router.patch("/{alert_id}/status")
def update_status(alert_id: str, update: AlertStatusUpdate, db: Session = Depends(get_db)):
    row = db.execute(text("UPDATE alerts SET status=:status, updated_at=NOW() WHERE alert_id=CAST(:id AS uuid) RETURNING alert_id, status, updated_at"), {"id": alert_id, "status": update.status}).mappings().first()
    if row is None: raise HTTPException(status_code=404, detail="Alert not found.")
    db.commit()
    return {"id": str(row["alert_id"]), "status": row["status"], "updated_at": iso(row["updated_at"])}


@router.get("/{alert_id}/report")
def get_report(alert_id: str, db: Session = Depends(get_db)):
    alert = detail_payload(db, alert_id); buffer = BytesIO(); doc = SimpleDocTemplate(buffer, pagesize=A4, title=f"Phoenix incident {alert['id']}"); styles = getSampleStyleSheet(); normal = styles["BodyText"]
    def p(value: str): return Paragraph(value.replace("&", "&amp;"), normal)
    risk = alert["risk_breakdown"]; facility = alert["facility"]; classification = alert["classification"]
    story = [Paragraph("PHOENIX Incident Report", styles["Title"]), Spacer(1, 12), p(f"<b>Alert summary:</b> {alert['severity'].title()} incident, risk score {alert['risk_score']:.1f}/100. Status: {alert['status']}.'"), p(f"<b>Facility context:</b> {facility['name']} ({facility['type'] or 'type unavailable'}), at {facility['location']['latitude']}, {facility['location']['longitude']}."), Spacer(1, 8), Paragraph("Risk assessment", styles["Heading2"]), p(f"Population exposed: {risk['population_exposed'] or 0}. Estimated emissions: {risk['estimated_emissions'] or 0}. FRP deviation ratio: {risk['frp_deviation_ratio'] or 'unavailable'}. Wind direction: {risk['wind_direction'] or 'unavailable'}."), Paragraph("Classification", styles["Heading2"]), p(f"{classification['label']} (confidence: {classification['confidence'] or 0:.0%})."), Paragraph("Reason codes", styles["Heading2"]), p("; ".join(map(str, alert['reasons'].get('risk_reason_codes', []))) or "No reason codes available."), Paragraph("Timeline", styles["Heading2"]), p("; ".join(f"{x['at']}: {x['label']}" for x in alert['timeline']))]
    doc.build(story); buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="phoenix-alert-{alert_id}.pdf"'})
