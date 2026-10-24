from math import radians, sin, cos, asin, sqrt
from datetime import datetime, timedelta, timezone

def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 6371.0 * 2 * asin(sqrt(min(1.0, a)))

def find_duplicate_candidates(report, candidates, radius_km: float = 0.15, window_days: int = 90) -> list[int]:
    """Suggest same-category reports nearby in space and time; never merges or deletes."""
    if report.latitude is None or report.longitude is None:
        return []
    found = []
    for other in candidates:
        if other.id == report.id or other.latitude is None or other.longitude is None:
            continue
        if other.category != report.category:
            continue
        created_at = getattr(other, "created_at", None)
        report_at = getattr(report, "created_at", None)
        if created_at is not None and report_at is not None:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if report_at.tzinfo is None:
                report_at = report_at.replace(tzinfo=timezone.utc)
            if abs(report_at - created_at) > timedelta(days=window_days):
                continue
        if distance_km(report.latitude, report.longitude, other.latitude, other.longitude) <= radius_km:
            found.append(other.id)
    return found
