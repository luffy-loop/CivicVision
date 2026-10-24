from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

def utcnow():
    return datetime.now(timezone.utc)

class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(140), default="Road condition report")
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(40), default="unknown")
    status: Mapped[str] = mapped_column(String(30), default="pending_review", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium", index=True)
    priority_reason: Mapped[str] = mapped_column(Text, default="Human review required.")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detector_mode: Mapped[str] = mapped_column(String(30), default="demo")
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    inference_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    detections_json: Mapped[str] = mapped_column(Text, default="[]")
    location_accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tracking_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    idempotency_key_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    assigned_team: Mapped[str | None] = mapped_column(String(120), nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    history: Mapped[list["StatusEvent"]] = relationship(back_populates="report", cascade="all, delete-orphan", order_by="StatusEvent.created_at")
    resolution_evidence: Mapped[list["ResolutionEvidence"]] = relationship(back_populates="report", cascade="all, delete-orphan", order_by="ResolutionEvidence.created_at")

class StatusEvent(Base):
    __tablename__ = "status_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), index=True)
    old_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(Text, default="")
    actor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    report: Mapped[Report] = relationship(back_populates="history")

class ResolutionEvidence(Base):
    __tablename__ = "resolution_evidence"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), index=True)
    image_path: Mapped[str] = mapped_column(String(500))
    note: Mapped[str] = mapped_column(Text, default="")
    submitted_by: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    report: Mapped[Report] = relationship(back_populates="resolution_evidence")
