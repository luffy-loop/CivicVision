from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import csv
import io
import secrets
from time import perf_counter
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query, Header
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from PIL import Image
from app.core.config import get_settings
from app.db import get_db
from app.models import Report, StatusEvent
from app.schemas import ScanResponse, Detection, ReportOut, ReportDetail, MetricsOut
from app.services.detector import inspect_image, predict
from app.services.triage import estimate_priority, normalized_kind
from app.services.duplicates import find_duplicate_candidates
from app.services.workflow import ALLOWED_TRANSITIONS, transition_allowed

router = APIRouter(prefix="/api")
settings = get_settings()
ALLOWED_STATUSES = {"pending_review", "verified", "in_progress", "resolved", "rejected"}
ALLOWED_CATEGORIES = {"pothole", "crack", "other", "unknown"}

async def read_upload(file: UploadFile) -> bytes:
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=415, detail="Upload a JPG, PNG or WebP image.")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    chunks, size = [], 0
    while True:
        chunk = await file.read(1024 * 512)
        if not chunk:
            break
        size += len(chunk)
        if size > max_bytes:
            raise HTTPException(status_code=413, detail=f"Image exceeds the {settings.max_upload_mb} MB upload limit.")
        chunks.append(chunk)
    if not chunks:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")
    return b"".join(chunks)

def require_reviewer(x_reviewer_key: str | None = Header(None)) -> None:
    """Shared-key gate for the local reviewer API; production should use user accounts and roles."""
    if not settings.reviewer_api_key:
        raise HTTPException(status_code=503, detail="Reviewer actions are disabled until REVIEWER_API_KEY is configured.")
    if not x_reviewer_key or not secrets.compare_digest(x_reviewer_key, settings.reviewer_api_key):
        raise HTTPException(status_code=401, detail="A valid reviewer credential is required.")

@router.get("/health")
def health():
    return {"status": "ok", "service": "civicvision-api", "mode": "model" if settings.model_path else ("demo" if settings.demo_mode else "unconfigured")}

@router.post("/scan", response_model=ScanResponse)
async def scan(file: UploadFile = File(...)):
    data = await read_upload(file)
    image, quality = inspect_image(data)
    started = perf_counter()
    mode, detections, note = predict(image)
    inference_ms = (perf_counter() - started) * 1000
    if quality["too_dark"] or quality["too_bright"] or quality["low_contrast"]:
        note += " Image quality warning: results may be less reliable; consider taking another photo."
    return ScanResponse(
        mode=mode,
        model_version=settings.model_version if mode == "model" else None,
        inference_ms=round(inference_ms, 2),
        image_width=image.width,
        image_height=image.height,
        detections=[Detection(**d) for d in detections],
        note=note,
    )

@router.post("/reports", response_model=ReportOut, status_code=201)
async def create_report(
    file: UploadFile = File(...),
    title: str = Form("Road condition report"),
    description: str = Form(""),
    category_override: str | None = Form(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    db: Session = Depends(get_db),
):
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail="Provide both latitude and longitude, or neither.")
    if latitude is not None and not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(status_code=422, detail="Coordinates are outside valid geographic ranges.")
    if category_override is not None and category_override not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=422, detail="Unsupported report category.")
    title = title.strip()[:140] or "Road condition report"
    description = description.strip()[:3000]
    data = await read_upload(file)
    image, _quality = inspect_image(data)
    mode, detections, _note = predict(image)
    labels = [d["label"].lower() for d in detections]
    kinds = [normalized_kind(label) for label in labels]
    category = category_override or ("pothole" if "pothole" in kinds else ("crack" if "crack" in kinds else "unknown"))
    priority = estimate_priority(detections) if mode == "model" else "review"
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = ".jpg"
    safe_name = f"{uuid4().hex}{suffix}"
    # Re-encode to strip EXIF metadata and normalize the saved image.
    image.save(upload_dir / safe_name, format="JPEG", quality=88, optimize=True)
    report = Report(
        title=title, description=description, category=category, status="pending_review",
        priority=priority, confidence=max((d["confidence"] for d in detections), default=None),
        latitude=latitude, longitude=longitude, image_path=str(upload_dir / safe_name),
        image_name=file.filename or "uploaded-image", detector_mode=mode,
    )
    db.add(report)
    db.flush()
    db.add(StatusEvent(report_id=report.id, old_status=None, new_status="pending_review", note="Report submitted"))
    db.commit()
    db.refresh(report)
    return report

@router.get("/reports", response_model=list[ReportOut])
def list_reports(
    status: str | None = Query(None),
    category: str | None = Query(None),
    search: str | None = Query(None, min_length=1, max_length=140),
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Report)
    if status:
        if status not in ALLOWED_STATUSES:
            raise HTTPException(status_code=422, detail="Unsupported status filter.")
        query = query.filter(Report.status == status)
    if category:
        if category not in ALLOWED_CATEGORIES:
            raise HTTPException(status_code=422, detail="Unsupported category filter.")
        query = query.filter(Report.category == category)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter((Report.title.ilike(term)) | (Report.description.ilike(term)))
    return query.order_by(Report.created_at.desc()).offset(offset).limit(limit).all()

@router.get("/reports/{report_id}", response_model=ReportDetail)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report

@router.get("/reports/{report_id}/image")
def report_image(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or not report.image_path or not Path(report.image_path).is_file():
        raise HTTPException(status_code=404, detail="Report image not found.")
    return FileResponse(report.image_path, media_type="image/jpeg", filename=f"civicvision-report-{report.id}.jpg")

@router.patch("/reports/{report_id}/status", response_model=ReportOut)
def update_status(report_id: int, status: str = Form(...), note: str = Form(""), db: Session = Depends(get_db), _reviewer: None = Depends(require_reviewer)):
    if status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=422, detail=f"Status must be one of: {', '.join(sorted(ALLOWED_STATUSES))}.")
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    old = report.status
    if not transition_allowed(old, status):
        raise HTTPException(status_code=409, detail=f"Transition from {old.replace('_', ' ')} to {status.replace('_', ' ')} is not allowed.")
    if status == old:
        return report
    report.status = status
    report.updated_at = datetime.now(timezone.utc)
    db.add(StatusEvent(report_id=report.id, old_status=old, new_status=status, note=note.strip()[:1000]))
    db.commit()
    db.refresh(report)
    return report

@router.get("/reports/{report_id}/duplicates")
def duplicates(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    candidates = db.query(Report).filter(Report.id != report_id).all()
    ids = find_duplicate_candidates(report, candidates, settings.duplicate_radius_km, settings.duplicate_window_days)
    return {"report_id": report_id, "candidate_ids": ids, "requires_human_review": True, "strategy": {"radius_km": settings.duplicate_radius_km, "window_days": settings.duplicate_window_days, "category_must_match": True, "image_similarity": "not evaluated"}}

@router.get("/metrics", response_model=MetricsOut)
def metrics(db: Session = Depends(get_db)):
    total = db.query(func.count(Report.id)).scalar() or 0
    by_status_rows = db.query(Report.status, func.count(Report.id)).group_by(Report.status).all()
    by_category_rows = db.query(Report.category, func.count(Report.id)).group_by(Report.category).all()
    statuses = dict(by_status_rows)
    return MetricsOut(
        total=total,
        pending=statuses.get("pending_review", 0),
        in_progress=statuses.get("in_progress", 0),
        resolved=statuses.get("resolved", 0),
        high_priority=db.query(func.count(Report.id)).filter(Report.priority == "high").scalar() or 0,
        by_category=dict(by_category_rows),
        by_status=statuses,
    )

@router.get("/reports-export.csv")
def export_reports(
    status: str | None = Query(None),
    category: str | None = Query(None),
    search: str | None = Query(None, min_length=1, max_length=140),
    db: Session = Depends(get_db),
):
    query = db.query(Report)
    if status:
        if status not in ALLOWED_STATUSES:
            raise HTTPException(status_code=422, detail="Unsupported status filter.")
        query = query.filter(Report.status == status)
    if category:
        if category not in ALLOWED_CATEGORIES:
            raise HTTPException(status_code=422, detail="Unsupported category filter.")
        query = query.filter(Report.category == category)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter((Report.title.ilike(term)) | (Report.description.ilike(term)))
    rows = query.order_by(Report.created_at.desc()).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id","title","category","status","priority","latitude","longitude","detector_mode","created_at"])
    for r in rows:
        safe_title = "'" + r.title if r.title.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else r.title
        writer.writerow([r.id,safe_title,r.category,r.status,r.priority,r.latitude,r.longitude,r.detector_mode,r.created_at.isoformat()])
    buffer.seek(0)
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers={"Content-Disposition":"attachment; filename=civicvision-reports.csv"})
