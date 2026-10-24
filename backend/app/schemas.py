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
    created_at: datetime

class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    category: str
    status: str
    priority: str
    confidence: float | None
    latitude: float | None
    longitude: float | None
    image_name: str | None
    detector_mode: str
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def image_url(self) -> str | None:
        return f"/api/reports/{self.id}/image" if self.image_name else None

class ReportDetail(ReportOut):
    history: list[StatusEventOut] = []

class MetricsOut(BaseModel):
    total: int
    pending: int
    in_progress: int
    resolved: int
    high_priority: int
    by_category: dict[str, int]
    by_status: dict[str, int]
