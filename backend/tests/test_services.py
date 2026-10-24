from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from app.services.duplicates import distance_km, find_duplicate_candidates
from app.services.triage import estimate_priority
from app.services.workflow import transition_allowed

def test_distance_zero():
    assert distance_km(17.0, 78.0, 17.0, 78.0) == 0

def test_distance_nearby_is_small():
    assert distance_km(17.0, 78.0, 17.001, 78.0) < 1

def test_duplicate_suggestions_require_same_category_and_proximity():
    report = SimpleNamespace(id=1, latitude=17.0, longitude=78.0, category="pothole")
    candidates = [
        SimpleNamespace(id=2, latitude=17.0001, longitude=78.0001, category="pothole"),
        SimpleNamespace(id=3, latitude=17.0001, longitude=78.0001, category="crack"),
        SimpleNamespace(id=4, latitude=18.0, longitude=79.0, category="pothole"),
    ]
    assert find_duplicate_candidates(report, candidates) == [2]

def test_priority_is_explicitly_rule_based():
    assert estimate_priority([]) == "review"
    assert estimate_priority([{"label":"pothole"}]) == "medium"
    assert estimate_priority([{"label":"pothole"},{"label":"pothole"}]) == "high"
    assert estimate_priority([{"label":"D00"}]) == "low"
    assert estimate_priority([{"label":"D40"}]) == "medium"

def test_duplicate_suggestions_respect_time_window():
    now = datetime.now(timezone.utc)
    report = SimpleNamespace(id=1, latitude=17.0, longitude=78.0, category="pothole", created_at=now)
    candidates = [
        SimpleNamespace(id=2, latitude=17.0001, longitude=78.0001, category="pothole", created_at=now-timedelta(days=30)),
        SimpleNamespace(id=3, latitude=17.0001, longitude=78.0001, category="pothole", created_at=now-timedelta(days=120)),
    ]
    assert find_duplicate_candidates(report, candidates, window_days=90) == [2]

def test_report_status_transitions_are_restricted():
    assert transition_allowed("pending_review", "verified")
    assert transition_allowed("in_progress", "resolved")
    assert transition_allowed("resolved", "in_progress")
    assert not transition_allowed("pending_review", "resolved")
    assert not transition_allowed("rejected", "verified")
