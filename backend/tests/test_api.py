from fastapi.testclient import TestClient
from app.main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db import Base, get_db
from app.models import Report, StatusEvent

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_readiness():
    response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"

def test_metrics_empty_or_valid():
    response = client.get("/api/metrics")
    assert response.status_code == 200
    payload = response.json()
    assert "total" in payload
    assert "by_status" in payload

def test_invalid_upload_type_rejected():
    response = client.post("/api/scan", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 415

def test_status_update_fails_closed_without_reviewer_key(monkeypatch):
    from app.api import routes
    monkeypatch.setattr(routes.settings, "reviewer_api_key", "")
    response = client.patch("/api/reports/999999/status", data={"status": "verified"})
    assert response.status_code == 503

def test_status_update_rejects_invalid_reviewer_key(monkeypatch):
    from app.api import routes
    monkeypatch.setattr(routes.settings, "reviewer_api_key", "test-reviewer-key")
    response = client.patch("/api/reports/999999/status", data={"status": "verified"}, headers={"X-Reviewer-Key": "wrong"})
    assert response.status_code == 401

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
    monkeypatch.setattr(__import__("app.api.routes", fromlist=["settings"]).settings, "reviewer_api_key", "integration-key")
    with TestingSession() as db:
        reports = [Report(title=f"filter-fixture-{index}", description="sample", category="pothole", status="pending_review", priority="review", detector_mode="demo") for index in range(3)]
        db.add_all(reports)
        db.flush()
        for report in reports:
            db.add(StatusEvent(report_id=report.id, old_status=None, new_status="pending_review", note="submitted"))
        db.commit()
        report_id = reports[0].id
    first = client.get("/api/reports", params={"search": "filter-fixture", "limit": 1, "offset": 0})
    second = client.get("/api/reports", params={"search": "filter-fixture", "limit": 1, "offset": 1})
    assert first.status_code == second.status_code == 200
    assert first.json()[0]["id"] != second.json()[0]["id"]
    assert client.get("/api/reports-export.csv", params={"search": "filter-fixture"}).text.count("filter-fixture") == 3
    rejected = client.patch(f"/api/reports/{report_id}/status", data={"status": "resolved"}, headers={"X-Reviewer-Key": "integration-key"})
    assert rejected.status_code == 409
    accepted = client.patch(f"/api/reports/{report_id}/status", data={"status": "verified"}, headers={"X-Reviewer-Key": "integration-key"})
    assert accepted.status_code == 200
    detail = client.get(f"/api/reports/{report_id}")
    assert [event["new_status"] for event in detail.json()["history"]] == ["pending_review", "verified"]
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
    response = client.post("/api/reports", data={"title": "User corrected category", "category_override": "crack", "latitude": "17", "longitude": "78"}, files={"file": ("road.jpg", payload.getvalue(), "image/jpeg")})
    assert response.status_code == 201
    report = response.json()
    assert report["category"] == "crack"
    assert report["detector_mode"] == "demo"
    image_response = client.get(report["image_url"])
    assert image_response.status_code == 200
    detail = client.get(f"/api/reports/{report['id']}")
    assert detail.json()["history"][0]["new_status"] == "pending_review"
    engine.dispose()
