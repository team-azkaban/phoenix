from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import alerts as alerts_api
from db.database import get_db
from services.alert_engine import evaluate_alert


class Result:
    def __init__(self, rows): self.rows = rows
    def mappings(self): return self
    def all(self): return self.rows
    def first(self): return self.rows[0] if self.rows else None
    def one(self): return self.rows[0]


class ListDb:
    def __init__(self): self.params = None
    def execute(self, _query, params):
        self.params = params
        return Result([{"alert_id": "11111111-1111-1111-1111-111111111111", "event_id": "22222222-2222-2222-2222-222222222222", "severity": "critical", "risk_score": 91.0, "status": "new", "created_at": datetime.now(timezone.utc), "facility_name": "Test Refinery", "classification": "industrial_fire"}])


def client_for(db):
    app = FastAPI(); app.include_router(alerts_api.router); app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_get_alerts_applies_filters():
    db = ListDb(); response = client_for(db).get("/alerts?severity=critical&status=new&limit=10")
    assert response.status_code == 200
    assert response.json()["alerts"][0]["facility_name"] == "Test Refinery"
    assert db.params["severity"] == "critical" and db.params["status"] == "new"


def test_alert_detail_has_expected_sections(monkeypatch):
    monkeypatch.setattr(alerts_api, "detail_payload", lambda _db, _id: {"id": _id, "facility": {}, "classification": {}, "frp_series": {}, "risk_breakdown": {}, "timeline": []})
    response = client_for(ListDb()).get("/alerts/11111111-1111-1111-1111-111111111111")
    assert response.status_code == 200
    assert {"facility", "classification", "frp_series", "risk_breakdown", "timeline"} <= response.json().keys()


def test_patch_rejects_invalid_status():
    response = client_for(ListDb()).patch("/alerts/11111111-1111-1111-1111-111111111111/status", json={"status": "active"})
    assert response.status_code == 422


def test_report_is_a_pdf(monkeypatch):
    monkeypatch.setattr(alerts_api, "detail_payload", lambda _db, _id: {"id": _id, "severity": "critical", "risk_score": 91.0, "status": "new", "facility": {"name": "Test Refinery", "type": "refinery", "location": {"latitude": 21.6, "longitude": 72.5}}, "classification": {"label": "industrial_fire", "confidence": .9}, "risk_breakdown": {"population_exposed": 10, "estimated_emissions": 3, "frp_deviation_ratio": 2, "wind_direction": 90}, "reasons": {"risk_reason_codes": ["High FRP"]}, "timeline": [{"at": "2026-01-01T00:00:00+00:00", "label": "Alert created"}]})
    response = client_for(ListDb()).get("/alerts/11111111-1111-1111-1111-111111111111/report")
    assert response.status_code == 200 and response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


class EngineDb:
    def __init__(self): self.alert = None; self.inserts = 0
    def execute(self, query, _params):
        sql = str(query)
        if "FROM risk_scores" in sql: return Result([{"risk_score": 85.0, "severity": "critical", "reasons": ["High FRP"], "created_at": datetime.now(timezone.utc)}])
        if "FROM classifications" in sql: return Result([{"classification": "industrial_fire", "confidence": .9, "reasons": {}}])
        if "FROM alerts" in sql: return Result([self.alert] if self.alert else [])
        if "INSERT INTO alerts" in sql:
            self.inserts += 1; self.alert = {"alert_id": "33333333-3333-3333-3333-333333333333", "severity": "critical", "risk_score": 85.0, "reasons": {}, "status": "new", "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}; return Result([self.alert])
        raise AssertionError(sql)


def test_alert_engine_is_idempotent_for_unchanged_score():
    db = EngineDb(); evaluate_alert(db, "22222222-2222-2222-2222-222222222222"); evaluate_alert(db, "22222222-2222-2222-2222-222222222222")
    assert db.inserts == 1
