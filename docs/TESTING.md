# Testing and local verification

## Backend

```powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q app scripts tests migrations
```

Tests cover health/readiness, CORS preflight, protected API access/login, invalid uploads, pixel limits, demo zero-prediction behavior, citizen report creation/idempotency/tracking, location metadata, private image access, search/pagination, allowed status transitions and actor attribution, duplicate matching, legacy SQLite migration, and dataset tooling. API tests use an in-memory SQLite database for report writes.

## Frontend

```powershell
cd frontend
npm ci
npm run test
npm run lint
npm run build
```

The built-in Node test runner covers API URL/session/error handling plus photo validation and camera/GPS failure messages. Type checking, unit tests and build do not validate actual camera or GPS permission behavior.

## Local smoke check

Configure named authority users and the token signing secret in `backend/.env`, then run `uvicorn app.main:app --reload` from `backend/` and `npm run dev` from `frontend/`. The citizen flow is `/report`; authority workspace is `/` and requires sign-in. Verify camera permission/denial, photo fallback and retake, GPS denial/manual coordinates, submit/retry, copy the complaint ID and private tracking key, check status at `/track`, and then confirm the same report and evidence appear after authority sign-in. Use HTTPS or localhost for browser camera and geolocation APIs.

Set `AUTO_MIGRATE=false` in production and run `alembic upgrade head` as a release step. No PostgreSQL instance, hosted deployment, production storage, actual mobile device, configured model, or real dataset has been verified here.
