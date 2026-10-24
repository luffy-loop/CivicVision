# Feature scope

## Implemented in this repository

- Citizen camera-first page at `/report`: rear-camera preference, automatic permission prompt on supported secure origins, visible start/retry controls, camera switching, supported torch toggle, captured photo review/retake, and image-picker fallback.
- GPS request after a user action, accuracy and capture timestamp, editable coordinates, denied/unavailable handling, and report submission without a location. Coordinates are never inferred or defaulted.
- Capture-then-detect using the configured backend model. Demo mode is explicitly shown and returns zero detections; the report is still available for human review. Predictions are persisted with mode/version/latency metadata.
- Report submission includes an idempotency key, photo, optional category/details, optional GPS metadata and a random complaint-tracking key. Confirmation gives the CV ID and key. Retry with the same key returns the same report and rotates the tracking key.
- Citizen status lookup at `/track` using the complaint ID and private key. It returns status timestamps only, not the report image, coordinates or internal review notes.
- Authority login for named `reviewer` and `admin` accounts, expiring signed sessions, server-protected data/evidence APIs and username-attributed status history.
- Existing authority dashboard, filters, map and analytics remain. CSV export and evidence fetch use the authority session.
- Alembic schema migration, local-development automatic upgrade, explicit CORS origins, image validation/metadata stripping and a process-local public upload throttle.
- Existing YOLO conversion, validation, training and evaluation scripts.

## Requires configuration or remains incomplete

- No trained checkpoint or dataset is included. Real model predictions and performance results require a licensed dataset, training/evaluation and an operator-provided `MODEL_PATH`.
- Real-device Android/iOS camera and GPS behavior was not verified in this environment. Secure origin (HTTPS or localhost) and browser permission are required.
- Authority roles exist, but the current workspace does not implement separate admin-only administration screens or account recovery. Accounts are configured out-of-band.
- Assignment workflow, resolution evidence upload and after-repair verification are not implemented.
- Local image storage is not durable on ephemeral hosting. Private object storage, retention/deletion controls, backup/restore and malware scanning need external configuration.
- Upload rate limiting is per-process and unsuitable as the only control for a multi-worker public deployment.
- No notification integration, Telugu localization, date/ward analytics, reviewer label-correction pipeline, road-segment history or automated image similarity.
- Production Render/Vercel variables were not changed or deployment verified from this workspace.
