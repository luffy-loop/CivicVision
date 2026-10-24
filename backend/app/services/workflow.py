"""Allowed report status transitions for reviewer workflow."""

ALLOWED_TRANSITIONS = {
    "pending_review": {"verified", "rejected"},
    "verified": {"assigned", "in_progress", "rejected"},
    "assigned": {"in_progress", "verified"},
    "in_progress": {"resolved", "verified"},
    "resolved": {"in_progress"},
    "rejected": {"pending_review"},
}


def transition_allowed(current: str, requested: str) -> bool:
    return current == requested or requested in ALLOWED_TRANSITIONS.get(current, set())
