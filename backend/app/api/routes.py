from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import csv
import io
import secrets
import hashlib
import json
from time import perf_counter
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query, Header, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from PIL import Image
from app.core.config import get_settings
from app.core.auth import configuration_ready, get_authority, issue_token, verify_password, _users
from app.core.rate_limit import enforce_upload_limit
from app.db import get_db
from app.models import Report, StatusEvent, ResolutionEvidence
from app.schemas import ScanResponse, Detection, ReportOut, ReportDetail, MetricsOut, AuthorityLogin, AuthoritySession, ReportCreated, PublicTracking, AssignmentIn, ResolutionEvidenceOut
from app.services.detector import inspect_image, predict
from app.services.triage import estimate_priority, explain_priority, normalized_kind
from app.services.duplicates import find_duplicate_candidates
from app.services.workflow import ALLOWED_TRANSITIONS, transition_allowed

router = APIRouter(prefix="/api")
settings = get_settings()
ALLOWED_STATUSES = {"pending_review", "verified", "assigned", "in_progress", "resolved", "rejected"}
ALLOWED_CATEGORIES = {"pothole", "crack", "other", "unknown"}

def report_created(report: Report, tracking_token: str) -> ReportCreated:
    payload = ReportOut.model_validate(report).model_dump()
    payload["detections_json"] = report.detections_json or "[]"
    payload["tracking_token"] = tracking_token
    return ReportCreated.model_validate(payload)

@router.post("/auth/login", response_model=AuthoritySession)
def login(credentials: AuthorityLogin):
    if not configuration_ready():
        raise HTTPException(status_code=503, detail="Authority access is not configured. Set AUTHORITY_USERS and AUTH_TOKEN_SECRET.")
    user = _users().get(credentials.username)
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Username or password is incorrect.")
    token, ttl = issue_token(credentials.username, user["role"])
    return AuthoritySession(access_token=token, expires_in=ttl, username=credentials.username, role=user["role"])

@router.get("/auth/me")
def current_authority(authority: dict[str, str] = Depends(get_authority)):
    return authority

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

@router.get("/health")
def health():
    return {"status": "ok", "service": "civicvision-api", "mode": "model" if settings.model_path else ("demo" if settings.demo_mode else "unconfigured")}

@router.post("/scan", response_model=ScanResponse)
async def scan(request: Request, file: UploadFile = File(...)):
    enforce_upload_limit(request, "scan")
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

@router.post("/reports", response_model=ReportCreated, status_code=201)
async def create_report(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form("Road condition report"),
    description: str = Form(""),
    category_override: str | None = Form(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    location_accuracy_m: float | None = Form(None),
    location_captured_at: datetime | None = Form(None),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    enforce_upload_limit(request, "report")
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail="Provide both latitude and longitude, or neither.")
    if latitude is not None and not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(status_code=422, detail="Coordinates are outside valid geographic ranges.")
    if location_accuracy_m is not None and (location_accuracy_m <= 0 or location_accuracy_m > 100_000):
        raise HTTPException(status_code=422, detail="Location accuracy must be between 0 and 100,000 metres.")
    if latitude is None and location_accuracy_m is not None:
        raise HTTPException(status_code=422, detail="Location accuracy requires latitude and longitude.")
    if latitude is None and location_captured_at is not None:
        raise HTTPException(status_code=422, detail="Location timestamp requires latitude and longitude.")
    if category_override is not None and category_override not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=422, detail="Unsupported report category.")
    key_hash = None
    if idempotency_key:
        if len(idempotency_key) > 200:
            raise HTTPException(status_code=422, detail="The submission key is invalid.")
        key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
        existing = db.query(Report).filter(Report.idempotency_key_hash == key_hash).first()
        if existing:
            tracking_token = secrets.token_urlsafe(32)
            existing.tracking_token_hash = hashlib.sha256(tracking_token.encode()).hexdigest()
            db.commit()
            db.refresh(existing)
            return report_created(existing, tracking_token)
    title = title.strip()[:140] or "Road condition report"
    description = description.strip()[:3000]
    data = await read_upload(file)
    image, _quality = inspect_image(data)
    started = perf_counter()
    mode, detections, _note = predict(image)
    inference_ms = round((perf_counter() - started) * 1000, 2)
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
    tracking_token = secrets.token_urlsafe(32)
    report = Report(
        title=title, description=description, category=category, status="pending_review",
        priority=priority, confidence=max((d["confidence"] for d in detections), default=None),
        priority_reason=explain_priority(detections, mode),
        latitude=latitude, longitude=longitude, image_path=str(upload_dir / safe_name),
        image_name=file.filename or "uploaded-image", detector_mode=mode,
        model_version=settings.model_version if mode == "model" else None,
        inference_ms=inference_ms,
        detections_json=json.dumps(detections, separators=(",", ":")),
        location_accuracy_m=location_accuracy_m if latitude is not None else None,
        location_captured_at=location_captured_at if latitude is not None else None,
        tracking_token_hash=hashlib.sha256(tracking_token.encode()).hexdigest(),
        idempotency_key_hash=key_hash,
    )
    db.add(report)
    db.flush()
    db.add(StatusEvent(report_id=report.id, old_status=None, new_status="pending_review", note="Report submitted", actor="citizen"))
    db.commit()
    db.refresh(report)
    return report_created(report, tracking_token)

@router.get("/reports", response_model=list[ReportOut])
def list_reports(
    status: str | None = Query(None),
    category: str | None = Query(None),
    search: str | None = Query(None, min_length=1, max_length=140),
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    _authority: dict[str, str] = Depends(get_authority),
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
def get_report(report_id: int, db: Session = Depends(get_db), _authority: dict[str, str] = Depends(get_authority)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report

@router.get("/reports/{report_id}/image")
def report_image(report_id: int, db: Session = Depends(get_db), _authority: dict[str, str] = Depends(get_authority)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or not report.image_path or not Path(report.image_path).is_file():
        raise HTTPException(status_code=404, detail="Report image not found.")
    return FileResponse(report.image_path, media_type="image/jpeg", filename=f"civicvision-report-{report.id}.jpg", headers={"Cache-Control": "private, no-store"})

@router.get("/reports/{report_id}/resolution-evidence/{evidence_id}/image")
def resolution_image(report_id: int, evidence_id: int, db: Session = Depends(get_db), _authority: dict[str, str] = Depends(get_authority)):
    evidence = db.query(ResolutionEvidence).filter(ResolutionEvidence.id == evidence_id, ResolutionEvidence.report_id == report_id).first()
    if not evidence or not Path(evidence.image_path).is_file():
        raise HTTPException(status_code=404, detail="Repair evidence not found.")
    return FileResponse(evidence.image_path, media_type="image/jpeg", filename=f"civicvision-repair-{report_id}-{evidence_id}.jpg", headers={"Cache-Control":"private, no-store"})

@router.post("/reports/{report_id}/resolution-evidence", response_model=ReportDetail)
async def add_resolution_evidence(report_id: int, request: Request, file: UploadFile = File(...), note: str = Form(""), db: Session = Depends(get_db), authority: dict[str, str] = Depends(get_authority)):
    enforce_upload_limit(request, "resolution-evidence")
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    if report.status != "in_progress":
        raise HTTPException(status_code=409, detail="Move the assigned report to in progress before adding completion evidence.")
    image, _quality = inspect_image(await read_upload(file))
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    image_path = upload_dir / f"repair-{uuid4().hex}.jpg"
    image.save(image_path, format="JPEG", quality=88, optimize=True)
    evidence = ResolutionEvidence(report_id=report.id, image_path=str(image_path), note=note.strip()[:1000], submitted_by=authority["username"])
    now = datetime.now(timezone.utc)
    db.add(evidence)
    report.status = "resolved"
    report.updated_at = now
    event_note = "Repair completion evidence submitted" + (f": {note.strip()[:900]}" if note.strip() else "")
    db.add(StatusEvent(report_id=report.id, old_status="in_progress", new_status="resolved", note=event_note, actor=authority["username"]))
    try:
        db.commit()
        db.refresh(report)
    except Exception:
        db.rollback()
        image_path.unlink(missing_ok=True)
        raise
    return report

@router.get("/reports/{report_id}/tracking", response_model=PublicTracking)
def track_report(report_id: int, token: str = Header(..., alias="X-Tracking-Token"), db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    supplied = hashlib.sha256(token.encode()).hexdigest()
    if not report or not report.tracking_token_hash or not secrets.compare_digest(report.tracking_token_hash, supplied):
        raise HTTPException(status_code=404, detail="Tracking credentials were not recognized.")
    public_events = [{"old_status": item.old_status, "new_status": item.new_status, "note": "", "actor": None, "created_at": item.created_at} for item in report.history]
    return PublicTracking(id=report.id, title=report.title, category=report.category, status=report.status, created_at=report.created_at, updated_at=report.updated_at, history=public_events)

@router.patch("/reports/{report_id}/status", response_model=ReportOut)
def update_status(report_id: int, status: str = Form(...), note: str = Form(""), db: Session = Depends(get_db), authority: dict[str, str] = Depends(get_authority)):
    if status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=422, detail=f"Status must be one of: {', '.join(sorted(ALLOWED_STATUSES))}.")
    if status == "assigned":
        raise HTTPException(status_code=422, detail="Use the assignment action to set a responsible team.")
    if status == "resolved":
        raise HTTPException(status_code=422, detail="Submit repair completion evidence to resolve a report.")
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
    db.add(StatusEvent(report_id=report.id, old_status=old, new_status=status, note=note.strip()[:1000], actor=authority["username"]))
    db.commit()
    db.refresh(report)
    return report

@router.patch("/reports/{report_id}/assignment", response_model=ReportOut)
def assign_report(report_id: int, assignment: AssignmentIn, db: Session = Depends(get_db), authority: dict[str, str] = Depends(get_authority)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    if report.status not in {"verified", "assigned"}:
        raise HTTPException(status_code=409, detail="Verify the report before assigning a repair team.")
    team = assignment.team.strip()
    if not team:
        raise HTTPException(status_code=422, detail="A responsible team is required.")
    old = report.status
    now = datetime.now(timezone.utc)
    report.status = "assigned"
    report.assigned_team = team
    report.assigned_at = now
    report.assigned_by = authority["username"]
    report.updated_at = now
    db.add(StatusEvent(report_id=report.id, old_status=old, new_status="assigned", note=f"Assigned to {team}", actor=authority["username"]))
    db.commit()
    db.refresh(report)
    return report

@router.get("/reports/{report_id}/duplicates")
def duplicates(report_id: int, db: Session = Depends(get_db), _authority: dict[str, str] = Depends(get_authority)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    candidates = db.query(Report).filter(Report.id != report_id).all()
    ids = find_duplicate_candidates(report, candidates, settings.duplicate_radius_km, settings.duplicate_window_days)
    return {"report_id": report_id, "candidate_ids": ids, "requires_human_review": True, "strategy": {"radius_km": settings.duplicate_radius_km, "window_days": settings.duplicate_window_days, "category_must_match": True, "image_similarity": "not evaluated"}}

@router.get("/metrics", response_model=MetricsOut)
def metrics(db: Session = Depends(get_db), _authority: dict[str, str] = Depends(get_authority)):
    total = db.query(func.count(Report.id)).scalar() or 0
    by_status_rows = db.query(Report.status, func.count(Report.id)).group_by(Report.status).all()
    by_category_rows = db.query(Report.category, func.count(Report.id)).group_by(Report.category).all()
    statuses = dict(by_status_rows)
    return MetricsOut(
        total=total,
        pending=statuses.get("pending_review", 0),
        verified=statuses.get("verified", 0),
        assigned=statuses.get("assigned", 0),
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
    _authority: dict[str, str] = Depends(get_authority),
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
