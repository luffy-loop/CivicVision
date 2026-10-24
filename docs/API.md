# API reference

FastAPI's interactive OpenAPI page is available at `/docs` while the API runs.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Service and detector mode |
| `GET` | `/api/ready` | Database readiness (`SELECT 1`) |
| `POST` | `/api/auth/login` | Named authority account login; returns a short-lived Bearer token |
| `GET` | `/api/auth/me` | Check the current authority session |
| `POST` | `/api/scan` | Validate and inspect one image; returns boxes, confidence, mode and inference time |
| `POST` | `/api/reports` | Save a citizen report and return its one-time tracking key; multipart form and optional `Idempotency-Key` |
| `GET` | `/api/reports/{id}/tracking` | Public, capability-key protected minimal status timeline (`X-Tracking-Token`) |
| `GET` | `/api/reports` | Authority-only filter by `status`, `category`, `search`; page by `offset` and `limit` |
| `GET` | `/api/reports/{id}` | Authority-only report with status history and action attribution |
| `GET` | `/api/reports/{id}/image` | Authority-only private evidence image |
| `PATCH` | `/api/reports/{id}/status` | Authority-only status change, audit actor taken from the signed session |
| `PATCH` | `/api/reports/{id}/assignment` | Assign a verified report to a responsible team |
| `POST` | `/api/reports/{id}/resolution-evidence` | Authority-only after-repair photo and note; stores evidence and resolves an in-progress report |
| `GET` | `/api/reports/{id}/resolution-evidence/{evidence_id}/image` | Authority-only private completion evidence |
| `GET` | `/api/reports/{id}/duplicates` | Authority-only candidate IDs and matching strategy |
| `GET` | `/api/metrics` | Authority-only aggregated counts from stored records |
| `GET` | `/api/reports-export.csv` | Authority-only CSV with optional `status`, `category`, `search` filters |

Report submission fields: `file`, `title`, `description`, optional `category_override`, and optional paired `latitude`/`longitude`, `location_accuracy_m`, and `location_captured_at`. Image input is limited by `MAX_UPLOAD_MB` and `MAX_IMAGE_PIXELS`. Store the returned `tracking_token` securely; only its hash is retained by the service. Set `Authorization: Bearer <token>` on authority API calls.

Status transitions: pending review → verified/rejected; verified → in progress/rejected; in progress → resolved/verified; resolved → in progress; rejected → pending review. Repeated status updates are no-ops. A status event is stored for each accepted change and attributes named authority actions to the signed-in username.
