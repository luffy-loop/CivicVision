# Security notes

# Security notes

## Implemented controls

- Authority report list/detail, map data, metrics, exports, status changes, duplicate inspection and evidence require a short-lived signed Bearer session for a named reviewer/admin account. Passwords are configured as PBKDF2-SHA256 hashes; there is no public account creation or shared reviewer key.
- Public report tracking uses a random capability key. Only a SHA-256 hash is persisted; the tracking endpoint returns a limited status timeline and does not return images, descriptions, coordinates, or internal notes.
- Evidence is not mounted as a public static directory. The image endpoint requires authority authentication and sends `Cache-Control: private, no-store`.
- Public scan and report image requests have a process-local per-IP throttle. Uploads are size/type checked, decoded, dimension limited, EXIF-normalized and re-encoded under generated filenames.
- Report creation supports an idempotency header; retries return the existing report record and rotate its tracking secret to the returned value.
- CORS uses explicit origins. Do not add wildcard origins.

## Setup and remaining production work

Generate a password hash with `python scripts/create_authority_hash.py` from `backend/`. Configure `AUTHORITY_USERS` with one or more named accounts and roles (`reviewer` or `admin`), plus a cryptographically random `AUTH_TOKEN_SECRET` of at least 32 bytes. Keep both values in the host's secret manager. The browser keeps an expiring session in `sessionStorage`; use HTTPS and a restrictive Content Security Policy.

The in-process upload throttle is a single-worker guardrail and resets on restart. Configure a distributed API rate limit/WAF at the edge before public traffic. Local file storage is suitable only for development or a persistent mounted disk. Render's ephemeral filesystem is not durable; configure private object storage, signed/authorized image access, retention and backups before production. Review location/image consent, deletion requests, backup restore and operational alerting. PostgreSQL and a tested migration/backup deployment have not been verified here.

`REVIEWER_API_KEY` is no longer used. Existing deployment secrets should be removed after rolling out the account-based configuration.
