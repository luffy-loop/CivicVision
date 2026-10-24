from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, computed_field

class Detection(BaseModel):
    label: str
    confidence: float = Field(ge=0, le=1)
    box: list[float] = Field(min_length=4, max_length=4)

class ScanResponse(BaseModel):
    mode: str
    model_version: str | None = None
    inference_ms: float
    image_width: int
    image_height: int
    detections: list[Detection]
    note: str

class StatusEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    old_status: str | None
    new_status: str
    note: str
    actor: str | None = None
    created_at: datetime

class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    category: str
    status: str
    priority: str
    priority_reason: str = "Human review required."
    confidence: float | None
    latitude: float | None
    longitude: float | None
    image_name: str | None
    detector_mode: str
    model_version: str | None = None
    inference_ms: float | None = None
    detections_json: str | None = Field(default="[]", exclude=True)
    location_accuracy_m: float | None = None
    location_captured_at: datetime | None = None
    assigned_team: str | None = None
    assigned_at: datetime | None = None
    assigned_by: str | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def image_url(self) -> str | None:
        return f"/api/reports/{self.id}/image" if self.image_name else None

    @computed_field
    @property
    def detections(self) -> list[Detection]:
        import json
        return [Detection(**item) for item in json.loads(self.detections_json or "[]")]

class ResolutionEvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    note: str
    submitted_by: str
    created_at: datetime

    @computed_field
    @property
    def image_url(self) -> str:
        return f"/api/reports/{self.report_id}/resolution-evidence/{self.id}/image"

    report_id: int = Field(exclude=True)

class ReportDetail(ReportOut):
    history: list[StatusEventOut] = []
    resolution_evidence: list[ResolutionEvidenceOut] = []

class MetricsOut(BaseModel):
    total: int
    pending: int
    verified: int = 0
    assigned: int = 0
    in_progress: int
    resolved: int
    high_priority: int
    by_category: dict[str, int]
    by_status: dict[str, int]

class AuthorityLogin(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=200)

class AuthoritySession(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    username: str
    role: str

class ReportCreated(ReportOut):
    tracking_token: str

class PublicTracking(BaseModel):
    id: int
    title: str
    category: str
    status: str
    created_at: datetime
    updated_at: datetime
    history: list[StatusEventOut]

class AssignmentIn(BaseModel):
    team: str = Field(min_length=1, max_length=120)
