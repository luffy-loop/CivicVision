# API quick reference

- `GET /api/health` — service status and configured detector mode
- `POST /api/scan` — multipart `file` image; returns model/demo mode and detections
- `POST /api/reports` — multipart `file`, `title`, `description`, optional `latitude`, `longitude`
- `GET /api/reports` — list reports; optional `status`, `category`, `limit`
- `GET /api/reports/{id}` — report details and status history
- `PATCH /api/reports/{id}/status` — multipart `status`, optional `note`
- `GET /api/reports/{id}/duplicates` — nearby same-category candidate IDs; human review required
- `GET /api/metrics` — summary metrics
- `GET /api/reports-export.csv` — CSV export

Interactive OpenAPI documentation is available at `/docs`.
