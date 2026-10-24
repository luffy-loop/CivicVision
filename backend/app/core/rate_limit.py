"""Process-local guardrail for public image endpoints; use an edge/WAF limiter in production."""
from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from fastapi import HTTPException, Request

_events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_lock = Lock()

def enforce_upload_limit(request: Request, action: str, limit: int = 20) -> None:
    host = request.client.host if request.client else "unknown"
    key = (action, host)
    now = monotonic()
    with _lock:
        events = _events[key]
        while events and now - events[0] >= 60:
            events.popleft()
        if len(events) >= limit:
            raise HTTPException(status_code=429, detail="Too many image requests. Wait a minute and try again.", headers={"Retry-After":"60"})
        events.append(now)
        if len(_events) > 2048:
            expired = [item for item, values in _events.items() if not values or now - values[-1] >= 60]
            for item in expired:
                _events.pop(item, None)
