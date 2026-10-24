# API reference

FastAPI's interactive OpenAPI page is available at `/docs` while the API runs.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Service and detector mode |
| `GET` | `/api/ready` | Database readiness (`SELECT 1`) |
| `POST` | `/api/scan` | Validate and inspect one image; returns boxes, confidence, mode and inference time |
| `POST` | `/api/reports` | Save a report and initial status event; multipart form |
| `GET` | `/api/reports` | Filter by `status`, `category`, `search`; page by `offset` and `limit` |
| `GET` | `/api/reports/{id}` | Report with status history |
| `GET` | `/api/reports/{id}/image` | Report evidence image (currently public) |
| `PATCH` | `/api/reports/{id}/status` | Change status; requires `X-Reviewer-Key` |
| `GET` | `/api/reports/{id}/duplicates` | Candidate IDs and matching strategy |
| `GET` | `/api/metrics` | Aggregated counts from stored records |
| `GET` | `/api/reports-export.csv` | CSV with optional `status`, `category`, `search` filters |

Report submission fields: `file`, `title`, `description`, optional `category_override`, and optional paired `latitude`/`longitude`. Image input is limited by `MAX_UPLOAD_MB` and `MAX_IMAGE_PIXELS`.

Status transitions: pending review → verified/rejected; verified → in progress/rejected; in progress → resolved/verified; resolved → in progress; rejected → pending review. Repeated status updates are no-ops. A status event is stored for each accepted change. Reviewer audit actor identity is not available because the current reviewer credential is a shared key.
