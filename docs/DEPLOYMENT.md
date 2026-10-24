# Deployment guide

## Local Docker Compose

```powershell
Copy-Item backend/.env.example .env
# Generate a staff password hash from backend/ with python scripts/create_authority_hash.py
# Set AUTHORITY_USERS and AUTH_TOKEN_SECRET in the untracked root .env file.
docker compose up --build
```

Compose stores SQLite and private uploads in the `civicvision_data` volume. Nginx proxies only `/api` to FastAPI. `MODEL_PATH` must name a file available inside the backend container; Compose does not mount weights by default.

## PostgreSQL and schema updates

Install `psycopg[binary]`, set `DATABASE_URL` to a SQLAlchemy psycopg URL, and provide network access to a PostgreSQL service. For production, set `AUTO_MIGRATE=false` and run `alembic upgrade head` from `backend/` as a release step. PostgreSQL is supported in configuration, but no hosted PostgreSQL instance or production restore has been verified.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `APP_NAME` | API title |
| `ENVIRONMENT` | Environment label |
| `DATABASE_URL` | SQLite or PostgreSQL SQLAlchemy URL |
| `CORS_ORIGINS` | Comma-separated exact browser origins |
| `UPLOAD_DIR` | Private evidence storage directory |
| `MAX_UPLOAD_MB` | Maximum image upload size |
| `MAX_IMAGE_PIXELS` | Maximum decoded image pixel count |
| `MODEL_PATH` | Optional compatible trained checkpoint |
| `MODEL_VERSION` | Operator-supplied identifier reported by scan API |
| `DEMO_MODE` | Allow explicit zero-detection demo responses when weights are absent |
| `AUTHORITY_USERS` | JSON array of named users with `username`, `role`, and PBKDF2 `password_hash` |
| `AUTH_TOKEN_SECRET` | At least 32 random bytes used to sign authority sessions |
| `AUTH_TOKEN_TTL_MINUTES` | Session lifetime, capped at 24 hours |
| `AUTO_MIGRATE` | Apply Alembic migrations at startup; development/single instance only |
| `DUPLICATE_RADIUS_KM` | Spatial duplicate suggestion radius |
| `DUPLICATE_WINDOW_DAYS` | Time window for duplicate suggestions |

Generate a staff hash with `python scripts/create_authority_hash.py` from `backend/`, then configure for example `AUTHORITY_USERS=[{"username":"reviewer.one","role":"reviewer","password_hash":"<generated-hash>"}]`. Generate `AUTH_TOKEN_SECRET` with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Put both only in the deployment secret manager. Set `CORS_ORIGINS` to exact deployed web origins. Set `VITE_API_URL=https://civicvision-645x.onrender.com` in Vercel and rebuild the frontend. The repository does not contain a Render Blueprint, so the existing external Render root/start configuration must be reviewed in its dashboard before changing it.

Compose uses a persistent local named volume; that does not configure Render object storage. Public production still requires durable private image storage, distributed edge rate limiting, privacy/retention controls, monitored database backups, and restore tests. The included upload limit is process-local and is not a WAF.

## Release checklist

- Verify dataset/checkpoint licenses and record held-out model evaluation.
- Configure exact CORS origins, Vercel `VITE_API_URL`, named authority accounts, and rotate/remove any legacy shared-key secret.
- Run reviewed Alembic migrations before application traffic.
- Configure HTTPS, durable private image storage, retention/deletion and backups.
- Enable distributed rate limiting, monitoring and alerting.
- Verify `/api/health` and `/api/ready` on the deployed backend and test browser API requests from the deployed origin.
- Run the documented backend and frontend checks against the release candidate.
