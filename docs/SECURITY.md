# Security notes

This repository is a development/portfolio foundation. Do not expose it publicly as-is without hardening.

- Status updates require the shared `REVIEWER_API_KEY` sent as `X-Reviewer-Key`. The route returns 503 until configured and 401 for a missing or invalid key. This is not individual authentication or role-based authorization; do not expose the review workflow publicly.
- SQLite is used by default for easy local setup.
- Uploaded images are served from the API uploads directory.
- Report evidence is also served from `/api/reports/{id}/image` without authentication. Treat all stored images as public in this preview.
- Set CORS to exact production origins.
- Add authentication and authorization before enabling reviewer operations.
- Add rate limits, abuse protection, monitoring, secure secrets, backups and retention policies.
- Validate and scan files, restrict content types, and store uploads in private object storage for public deployment.
- Review privacy and consent before storing coordinates or images.
