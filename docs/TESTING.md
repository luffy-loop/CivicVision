# Testing and local verification

## Backend

```powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q app scripts tests
```

macOS/Linux: the same commands work after activating the project's virtual environment. Tests currently cover health/readiness, metrics response shape, unsupported uploads, image pixel limits, demo-mode zero predictions, reviewer-key fail-closed behavior, report creation/evidence/history, search/pagination, allowed status transitions, duplicate matching and deterministic VOC conversion. Some basic API tests read the configured local database; isolate it before running tests if the database contains important local work.

## Frontend

```powershell
cd frontend
npm ci
npm run lint
npm run build
```

## Manual smoke test

Run the API with `uvicorn app.main:app --reload` from `backend/` and Vite with `npm run dev` from `frontend/`. Check demo-mode scan response, image rejection, report submission, filters and pagination, report image/detail/history, map attribution and filters, CSV export, and analytics with an empty and populated database. Configure `REVIEWER_API_KEY` and verify authorized transitions and rejected invalid transitions.

No Playwright/browser automation, visual regression suite, PostgreSQL integration test, or deployed environment test is currently configured. A local Uvicorn startup/readiness check has been run, but the complete browser journey and responsive visual QA have not. Do not treat the manual plan as evidence that those checks ran.
