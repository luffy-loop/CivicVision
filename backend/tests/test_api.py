from fastapi.testclient import TestClient
from app.main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db import Base, get_db
from app.models import Report, StatusEvent
import json

def authority_headers(monkeypatch):
    from app.api import routes
    from app.core.auth import hash_password, issue_token
    monkeypatch.setattr(routes.settings, "authority_users", json.dumps([{"username":"reviewer.one","role":"reviewer","password_hash":hash_password("a-long-test-password")}]))
    monkeypatch.setattr(routes.settings, "auth_token_secret", "test-signing-secret-with-more-than-32-characters")
    token, _ = issue_token("reviewer.one", "reviewer")
    return {"Authorization": f"Bearer {token}"}

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_readiness():
    response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"

def test_production_frontend_cors_preflight():
    response = client.options("/api/metrics", headers={"Origin":"https://civicvision-ai-mocha.vercel.app","Access-Control-Request-Method":"GET"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://civicvision-ai-mocha.vercel.app"

def test_metrics_empty_or_valid(monkeypatch):
    response = client.get("/api/metrics", headers=authority_headers(monkeypatch))
    assert response.status_code == 200
    payload = response.json()
    assert "total" in payload
    assert "by_status" in payload

def test_invalid_upload_type_rejected():
    response = client.post("/api/scan", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 415

def test_authority_access_fails_closed_without_account_configuration(monkeypatch):
    from app.api import routes
    monkeypatch.setattr(routes.settings, "authority_users", "[]")
    monkeypatch.setattr(routes.settings, "auth_token_secret", "")
    assert client.get("/api/metrics").status_code == 503
    assert client.patch("/api/reports/999999/status", data={"status": "verified"}).status_code == 503

def test_authority_endpoints_reject_invalid_session(monkeypatch):
    authority_headers(monkeypatch)
    response = client.get("/api/reports", headers={"Authorization":"Bearer invalid"})
    assert response.status_code == 401

def test_authority_login_uses_password_hash_and_returns_expiring_session(monkeypatch):
    from app.api import routes
    from app.core.auth import hash_password
    monkeypatch.setattr(routes.settings, "authority_users", json.dumps([{"username":"staff","role":"admin","password_hash":hash_password("correct horse battery staple")}]))
    monkeypatch.setattr(routes.settings, "auth_token_secret", "test-signing-secret-with-more-than-32-characters")
    denied = client.post("/api/auth/login", json={"username":"staff","password":"incorrect"})
    assert denied.status_code == 401
    accepted = client.post("/api/auth/login", json={"username":"staff","password":"correct horse battery staple"})
    assert accepted.status_code == 200
    assert accepted.json()["role"] == "admin"
    assert accepted.json()["expires_in"] > 0

def test_scan_rejects_excessive_pixel_count(monkeypatch):
    from io import BytesIO
    from PIL import Image
    from app.api import routes
    image = Image.new("RGB", (12, 12), "white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    monkeypatch.setattr(routes.settings, "max_image_pixels", 100)
    response = client.post("/api/scan", files={"file": ("road.png", buffer.getvalue(), "image/png")})
    assert response.status_code == 413

def test_demo_scan_returns_no_predictions(monkeypatch):
    from io import BytesIO
    from PIL import Image
    from app.api import routes
    from app.services import detector
    monkeypatch.setattr(routes.settings, "model_path", "")
    monkeypatch.setattr(routes.settings, "demo_mode", True)
    monkeypatch.setattr(detector.settings, "model_path", "")
    monkeypatch.setattr(detector.settings, "demo_mode", True)
    image = Image.new("RGB", (96, 96), "white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    response = client.post("/api/scan", files={"file": ("road.png", buffer.getvalue(), "image/png")})
    assert response.status_code == 200
    assert response.json()["mode"] == "demo"
    assert response.json()["detections"] == []
    assert response.json()["inference_ms"] >= 0

def test_report_search_pagination_and_status_history(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()
    monkeypatch.setitem(app.dependency_overrides, get_db, override_get_db)
    headers = authority_headers(monkeypatch)
    with TestingSession() as db:
        reports = [Report(title=f"filter-fixture-{index}", description="sample", category="pothole", status="pending_review", priority="review", detector_mode="demo") for index in range(3)]
        db.add_all(reports)
        db.flush()
        for report in reports:
            db.add(StatusEvent(report_id=report.id, old_status=None, new_status="pending_review", note="submitted"))
        db.commit()
        report_id = reports[0].id
    first = client.get("/api/reports", params={"search": "filter-fixture", "limit": 1, "offset": 0}, headers=headers)
    second = client.get("/api/reports", params={"search": "filter-fixture", "limit": 1, "offset": 1}, headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json()[0]["id"] != second.json()[0]["id"]
    assert client.get("/api/reports-export.csv", params={"search": "filter-fixture"}, headers=headers).text.count("filter-fixture") == 3
    rejected = client.patch(f"/api/reports/{report_id}/status", data={"status": "resolved"}, headers=headers)
    assert rejected.status_code == 422
    accepted = client.patch(f"/api/reports/{report_id}/status", data={"status": "verified"}, headers=headers)
    assert accepted.status_code == 200
    detail = client.get(f"/api/reports/{report_id}", headers=headers)
    assert [event["new_status"] for event in detail.json()["history"]] == ["pending_review", "verified"]
    assert detail.json()["history"][-1]["actor"] == "reviewer.one"
    engine.dispose()

def test_report_creation_persists_image_category_and_initial_history(monkeypatch, tmp_path):
    from io import BytesIO
    from PIL import Image
    from app.api import routes
    from app.services import detector
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()
    monkeypatch.setitem(app.dependency_overrides, get_db, override_get_db)
    monkeypatch.setattr(routes.settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(routes.settings, "model_path", "")
    monkeypatch.setattr(routes.settings, "demo_mode", True)
    monkeypatch.setattr(detector.settings, "model_path", "")
    monkeypatch.setattr(detector.settings, "demo_mode", True)
    image = Image.new("RGB", (100, 100), "#999999")
    payload = BytesIO()
    image.save(payload, format="JPEG")
    response = client.post("/api/reports", data={"title": "User corrected category", "category_override": "crack", "latitude": "17", "longitude": "78", "location_accuracy_m":"14.5", "location_captured_at":"2026-10-24T10:00:00Z"}, files={"file": ("road.jpg", payload.getvalue(), "image/jpeg")}, headers={"Idempotency-Key":"test-citizen-submit-01"})
    assert response.status_code == 201
    report = response.json()
    assert report["category"] == "crack"
    assert report["detector_mode"] == "demo"
    assert report["location_accuracy_m"] == 14.5
    assert report["location_captured_at"].startswith("2026-10-24T10:00:00")
    assert report["detections"] == []
    assert report["tracking_token"]
    denied_image = client.get(report["image_url"])
    assert denied_image.status_code == 503
    headers = authority_headers(monkeypatch)
    image_response = client.get(report["image_url"], headers=headers)
    assert image_response.status_code == 200
    detail = client.get(f"/api/reports/{report['id']}", headers=headers)
    assert detail.json()["history"][0]["new_status"] == "pending_review"
    tracked = client.get(f"/api/reports/{report['id']}/tracking", headers={"X-Tracking-Token":report["tracking_token"]})
    assert tracked.status_code == 200
    assert "description" not in tracked.json() and "image_url" not in tracked.json()
    assert client.get(f"/api/reports/{report['id']}/tracking", headers={"X-Tracking-Token":"wrong"}).status_code == 404
    retry = client.post("/api/reports", data={"title": "Retry duplicate"}, files={"file": ("road.jpg", payload.getvalue(), "image/jpeg")}, headers={"Idempotency-Key":"test-citizen-submit-01"})
    assert retry.status_code == 201 and retry.json()["id"] == report["id"]
    assert retry.json()["tracking_token"] != report["tracking_token"]
    engine.dispose()

def test_assignment_and_resolution_evidence_are_authorized_and_attributed(monkeypatch, tmp_path):
    from io import BytesIO
    from PIL import Image
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()
    monkeypatch.setitem(app.dependency_overrides, get_db, override_get_db)
    from app.api import routes
    monkeypatch.setattr(routes.settings, "upload_dir", str(tmp_path / "private"))
    headers = authority_headers(monkeypatch)
    with TestingSession() as db:
        report = Report(title="Repair workflow", description="", category="pothole", status="verified", priority="medium", detector_mode="demo")
        db.add(report); db.commit(); report_id = report.id
    assigned = client.patch(f"/api/reports/{report_id}/assignment", json={"team":"Ward 4 roads"}, headers=headers)
    assert assigned.status_code == 200
    assert assigned.json()["status"] == "assigned" and assigned.json()["assigned_by"] == "reviewer.one"
    progressed = client.patch(f"/api/reports/{report_id}/status", data={"status":"in_progress"}, headers=headers)
    assert progressed.status_code == 200
    payload = BytesIO(); Image.new("RGB",(100,100),"#668866").save(payload,format="JPEG")
    resolved = client.post(f"/api/reports/{report_id}/resolution-evidence", data={"note":"Surface repaired and checked"}, files={"file":("after.jpg",payload.getvalue(),"image/jpeg")}, headers=headers)
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"
    assert len(resolved.json()["resolution_evidence"]) == 1
    image_url = resolved.json()["resolution_evidence"][0]["image_url"]
    assert client.get(image_url, headers=headers).status_code == 200
    assert client.get(image_url).status_code == 401
    assert [event["new_status"] for event in resolved.json()["history"]] == ["assigned","in_progress","resolved"]
    assert all(event["actor"] == "reviewer.one" for event in resolved.json()["history"])
    assert client.patch(f"/api/reports/{report_id}/status", data={"status":"resolved"}, headers=headers).status_code == 422
    engine.dispose()
