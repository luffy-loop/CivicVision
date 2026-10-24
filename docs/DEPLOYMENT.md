# Deployment guide

## Local Docker Compose

```powershell
Copy-Item backend/.env.example .env
docker compose up --build
```

On macOS/Linux, use `cp backend/.env.example .env`. Edit values before starting; Compose persists SQLite and uploads in the `civicvision_data` volume. The frontend is served by Nginx on port 8080 and proxies `/api` and `/uploads` to the backend. `MODEL_PATH` must name a file visible at that same path inside the container; Compose does not mount weights by default.

## PostgreSQL

Install the Python requirement `psycopg[binary]`, set `DATABASE_URL` to a SQLAlchemy psycopg URL, and provide network reachability to an existing PostgreSQL service. This repository does not provision PostgreSQL, run schema migrations, or verify a production database. Back up the database and test restores before accepting public reports.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `APP_NAME` | API title |
| `ENVIRONMENT` | Environment label |
| `DATABASE_URL` | SQLite or PostgreSQL SQLAlchemy URL |
| `CORS_ORIGINS` | Comma-separated exact browser origins |
| `UPLOAD_DIR` | Evidence storage directory |
| `MAX_UPLOAD_MB` | Maximum image upload size |
| `MAX_IMAGE_PIXELS` | Maximum decoded image pixel count |
| `MODEL_PATH` | Optional compatible trained checkpoint |
| `MODEL_VERSION` | Operator-supplied identifier reported by scan API |
| `DEMO_MODE` | Allow explicit zero-detection demo responses when weights are absent |
| `REVIEWER_API_KEY` | Shared key required for status changes in a controlled preview |
| `DUPLICATE_RADIUS_KM` | Spatial duplicate suggestion radius |
| `DUPLICATE_WINDOW_DAYS` | Time window for duplicate suggestions |

Use a unique secret outside source control. Do not use the shared-key reviewer gate for a public service. Public deployment requires individual authentication/roles, private evidence storage, HTTPS, rate limiting, a supported migration plan, monitoring, tested backups and a privacy/retention policy. These are not supplied by the current Compose files.

## Release checklist

- Verify dataset and checkpoint licenses and document model evaluation.
- Configure exact CORS origins and rotate all credentials.
- Add user identity and server-side roles before exposing reviewer operations.
- Replace public static upload access with authorized storage and retention controls.
- Apply reviewed database migrations and test backup recovery.
- Enable HTTPS, request limits, rate limiting, logs, metrics and alerting.
- Verify `/api/health` and `/api/ready` in the deployment environment.
- Run the documented backend and frontend checks against the release candidate.
