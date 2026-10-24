# API quick reference

- `GET /api/health` — service status and configured detector mode
- `POST /api/scan` — multipart `file` image; returns model/demo mode and detections
- `POST /api/auth/login` — JSON `username`, `password`; returns an expiring authority Bearer token
- `POST /api/reports` — multipart `file`, `title`, `description`, optional `latitude`, `longitude`, location accuracy/time, and `Idempotency-Key`
- `GET /api/reports/{id}/tracking` — citizen lookup with `X-Tracking-Token`
- `GET /api/reports` — authority-only list; optional `status`, `category`, `limit`
- `GET /api/reports/{id}` — authority-only report details and status history
- `PATCH /api/reports/{id}/status` — authority-only multipart `status`, optional `note`
- `GET /api/reports/{id}/duplicates` — nearby same-category candidate IDs; human review required
- `GET /api/metrics` — authority-only summary metrics
- `GET /api/reports-export.csv` — authority-only CSV export

Interactive OpenAPI documentation is available at `/docs`.
