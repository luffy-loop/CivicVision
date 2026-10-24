# Implementation status (verified 2026-10-24)

This report distinguishes local source checks from deployment, device, model and production infrastructure validation. A passing local check is not a production readiness certification.

## Implemented

- Retained the existing React, TypeScript, Vite dashboard and FastAPI API, including the mocha, platinum and pale-lavender theme.
- Added a mobile citizen report flow at `/report` and private status lookup at `/track`. Citizens can capture or upload a road photo, optionally share reviewed GPS coordinates, receive a one-time tracking key, and see a minimal status timeline.
- Kept detector behavior explicit: demo mode reports zero detections and says so; model version, inference time and detections are carried with reports when a configured model is used. No model is claimed to be trained or validated.
- Added named authority accounts with PBKDF2 password hashes and expiring HMAC-signed sessions. Authority report, metrics, export and evidence APIs require authentication. Public static upload serving has been removed.
- Added workflow audit actors, team assignment, status transition validation and required after-repair photo/note evidence before resolution. Public citizens see only the report status timeline.
- Added hashed citizen tracking tokens, idempotent submissions, location timestamp/accuracy metadata, upload validation, process-local request throttling and explicit CORS configuration.
- Added Alembic migrations and local automatic upgrades. Production deployment guidance calls for an explicit migration release step.
- Updated API, security, architecture, deployment, testing and feature documentation; added frontend API/citizen utility tests using Node's built-in test runner.

## Validation record

The following checks passed on the final source state:

- Backend `python -m pytest -q`: **21 passed** (one upstream Starlette/httpx deprecation warning).
- Backend `python -m compileall -q app scripts tests migrations`: passed.
- Frontend `npm run test`: **5 passed**.
- Frontend `npm run lint` and `npm run build`: passed.
- Local FastAPI smoke check: `/api/health` returned `ok` in demo mode and `/api/ready` returned `ready` after migrations. The authority reports route returned the expected `503` configuration message because no local authority account/secret is configured in this environment.
- Docker image build/config validation unavailable because Docker CLI is not installed.
- Browser smoke inspection covered authority login and the tracking page. Citizen camera permission and GPS were not exercised on an actual device. No deployed service was verified; the configured deployment URLs could not be reached by the available lookup tool.
- The originally reported 500 responses were backend/API failures, not React Router warnings. API health/readiness and migration startup now pass locally. The React DevTools notice and Router v7 future-flag warnings are informational.

## Remaining production prerequisites and limits

- Configure `AUTHORITY_USERS`, `AUTH_TOKEN_SECRET`, `CORS_ORIGINS`, database URL, and `AUTO_MIGRATE=false` for production. Run `alembic upgrade head` as a release step. Configure `VITE_API_URL` for the deployed frontend.
- No real road-damage dataset, licensed checkpoint, trained model, held-out model metrics, PostgreSQL service, or production deployment was available for validation. Detector demo mode is not a substitute for model evaluation.
- Local file storage and a process-local throttle are development guardrails. Before public production, configure durable private object storage, retention/deletion policy, backups, distributed rate limits/WAF and operational alerts.
- Reviewer and admin role values are authenticated, but per-action admin-only authorization and account lifecycle/recovery tooling are not implemented. Accounts are configured out of band.
- Docker builds, end-to-end deployment, live PostgreSQL migration/restore, and real-device camera/GPS permissions remain unverified.
