# Implementation status (verified 2026-10-24)

This is a source and local-test status report, not a production security review or model-performance claim.

## Implemented and locally checked

- Existing React, TypeScript, Vite and FastAPI application retained. Theme tokens now use the requested Mocha Brown `#6F4E37`, Platinum Silver `#E5E4E2`, and Pale Lavender `#E6E0F0` across the main navigation, actions, surfaces, forms, charts and map markers.
- Scanner validates image type/bytes/pixels, normalizes EXIF orientation, reports inference time/model version, and can render/download detection-box overlays in the browser. Demo mode still returns zero detections.
- Reports support category correction on submission, bounded search/filter/offset pagination, filtered CSV export, detail/evidence/history views, and an explicit allowed status-transition graph. Status writes require the configured shared reviewer key.
- Leaflet map uses OpenStreetMap tiles with attribution, status/category filters, map bounds fitting, loading/error/retry and no-coordinate states.
- Readiness endpoint checks the database connection. PostgreSQL driver dependency and Compose overrides are present; SQLite remains the local default.
- YOLO tools include a Pascal VOC converter, dHash/exact-image grouping before deterministic train/validation/test splitting, structure validation, reproducible training options and held-out evaluation metrics output.
- New project docs cover architecture, API, dataset/training, deployment and testing.

## Checks actually run

- Backend: `python -m pytest -q` — **17 passed**, with one upstream Starlette/httpx deprecation warning.
- Backend: `python -m compileall -q app scripts tests` — passed.
- Training tools: converter, validator and evaluator `--help` commands — passed. Synthetic converter regression test checks repeatable splits and exact-image grouping.
- Frontend: `npm run lint` and `npm run build` — passed on the final source state.
- Runtime: Uvicorn started successfully; `GET /api/ready` returned `{"status":"ready","database":"ok"}`. The process was stopped after verification.
- Compose YAML parsed with PyYAML. Docker config validation and image builds could not run because Docker CLI is not installed.
- Backend TestClient requests ran under elevated test execution because local socket access is denied in the sandbox. A real browser walkthrough was not performed.
- No real dataset, model training, model evaluation, PostgreSQL service, or public deployment was run.

## Remaining limitations

- The reviewer shared key is not citizen/reviewer/admin accounts, individual authentication, role authorization or attributable reviewer identity. Do not expose this preview workflow publicly.
- Report images remain publicly accessible via `/uploads` and the report-image API; private object storage, authorization, retention/deletion and malware scanning are absent.
- The schema still uses `Base.metadata.create_all`; Alembic migrations and PostgreSQL integration tests are not implemented.
- English/Telugu localization is not implemented. Date-range analytics and map filters are absent.
- Duplicate suggestions do not compare image similarity and cannot be confirmed/dismissed in a reviewer workflow. Road-change timelines/image comparison and reviewer classification corrections/export are absent.
- Creating a report after a scan reuploads and reruns inference. Scanner overlays are browser-rendered; there is no server-side annotated artifact or original/annotated comparison control.
- Converter grouping reduces exact and perceptual-image leakage but does not know capture sequence or geography. No false-positive/false-negative gallery or trained model metrics exist. Confirm dataset license directly with the linked Figshare record before reuse; it could not be verified here.
- Docker builds, end-to-end upload/report flows, responsive browser inspection and production deployment remain unverified.
