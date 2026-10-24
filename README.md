# CivicVision AI
**Community road-condition reporting with computer-vision assistance.**

CivicVision helps people submit road-damage reports, review image-based detections, track report status, and explore issues on a map. It is designed as a portfolio-ready full-stack foundation with a real API, persistent database, tests, container setup, and a polished responsive interface.

> **Important:** This repository does not ship trained road-damage weights or the RDD2022 dataset. Until you train and configure your own compatible detector, the API runs in clearly labelled demo mode and returns zero detections; demo mode only exercises the scan workflow.

## Features
- Responsive React/Vite interface with dashboard, scan workflow, report list, report detail, map and analytics.
- FastAPI backend with image validation, SQLite persistence by default, report status updates, metrics, health check and OpenAPI docs.
- Optional Ultralytics YOLO inference via `MODEL_PATH`; model weights are not bundled.
- Explicit demo mode when no model is configured.
- Report priorities are rule-based estimates, not measurements of real-world danger.
- Duplicate suggestions based on category, distance and a configurable time window; suggestions require human review.
- Image decoding, metadata-stripping report storage, browser-annotated scan downloads, model timing/version output, configurable upload and pixel limits, CORS configuration, API tests, Docker Compose and GitHub Actions.
- CSV export, report status history, report search/filtering/pagination and an English-only interface (localization is not implemented).

## Architecture
- `frontend/`: React + Vite + TypeScript + custom CSS, Leaflet + OpenStreetMap tiles.
- `backend/`: FastAPI, SQLAlchemy, Pillow, optional Ultralytics.
- `backend/app/services/detector.py`: model adapter and clearly labelled demo fallback.
- `backend/app/services/triage.py`: transparent, simple priority heuristics.
- `backend/app/services/duplicates.py`: candidate duplicate matching by location, category and time; never automatic merging.

Reviewer status changes require `REVIEWER_API_KEY` and the review dialog sends it only for the requested action. This is a shared-key gate for controlled previews, not user accounts or role-based authentication. Configure a unique secret locally; public deployments require individual identity and authorization.

## Run locally

### Requirements
- Python 3.11+
- Node.js 20+
- Git
- Optional: compatible YOLO weights and the Ultralytics package

### 1. Backend
Windows PowerShell:
```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```
macOS/Linux:
```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs

### 2. Frontend
In a second terminal:
```bash
cd frontend
npm install
npm run dev
```
Open the local URL printed by Vite. The frontend uses `/api` via Vite proxy to the backend.

### Optional real model
Install the optional dependency:
```bash
pip install ultralytics
```
Set `MODEL_PATH` in `backend/.env` to a compatible trained weights file path. The class names in the model must match the labels you expect. If the model is unavailable or fails to load, the API returns a safe service error rather than fabricating predictions. Restart the API after changing configuration.

### Tests
```bash
cd backend
pip install -r requirements-dev.txt
pytest
```
Frontend checks:
```bash
cd frontend
npm install
npm run lint
npm run build
```
Use `npm ci` in CI and Docker to install the exact lockfile versions.

### Docker
From the repository root:
```bash
docker compose up --build
```
Frontend: http://localhost:8080  
API docs: http://localhost:8000/docs

Docker Compose reads optional overrides from a root `.env` file. Set `REVIEWER_API_KEY` to enable status updates in the review dialog. Set `MODEL_PATH` only when the checkpoint is mounted at the same path inside the backend container; the Compose setup does not bundle or mount weights. For PostgreSQL, set `DATABASE_URL` to a SQLAlchemy psycopg URL and provide the database network/service separately.

## Training a detector
Follow [docs/DATASET_AND_TRAINING.md](docs/DATASET_AND_TRAINING.md) for RDD2022 sourcing and license verification, Pascal VOC conversion, perceptual grouping, validation, training and held-out evaluation commands. Neither data nor model weights are included, and no model results are claimed.

Validate YOLO labels before training with `python scripts/validate_yolo_dataset.py --data /path/to/data.yaml` from `backend/`. This checks normalized box structure, class IDs, annotation file presence, and exact-byte duplicate images across splits. It cannot detect adjacent video frames or geographic/sequence leakage; construct splits by source road/sequence before validation.

Useful references:
- RDD2022 project paper: https://arxiv.org/abs/2209.08538
- Ultralytics Python usage: https://docs.ultralytics.com/usage/python/
- Ultralytics training: https://docs.ultralytics.com/modes/train/
- FastAPI documentation: https://fastapi.tiangolo.com/
- React: https://react.dev/
- Vite: https://vite.dev/

## Project documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [Dataset and training](docs/DATASET_AND_TRAINING.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Security](docs/SECURITY.md)
- [Testing](docs/TESTING.md)
- [Features](docs/FEATURES.md)
- [Implementation status](docs/IMPLEMENTATION_STATUS.md)

## Production hardening checklist
This is a strong deployable project foundation, not a guarantee of production security or flawless operation. Before public launch:
- Use managed PostgreSQL instead of SQLite and run migrations (Alembic).
- Add authentication, account recovery, rate limiting, CSRF strategy if cookie auth is used, and role-based permissions.
- Put uploaded images in private object storage; define retention and deletion policies.
- Add antivirus/content scanning, image metadata stripping, abuse moderation and request quotas.
- Configure HTTPS, secrets management, trusted CORS origins and database backups.
- Add monitoring, structured logs, alerting, model versioning and load tests.
- Have a reviewer verify reports before they are treated as confirmed civic complaints.
- Check dataset and model licensing and Ultralytics licensing obligations before commercial use.
- Do not claim official municipal integration unless one is actually established.

## Evaluation metrics
Detection: per-class precision/recall/F1, mAP@0.5 and mAP@0.5:0.95, latency and model size.  
Product: API success rate, median/p95 latency, upload rejection behavior, duplicate suggestion precision, reviewer agreement and user task completion.  
Never present model confidence as defect severity or treat a photo-only estimate as an engineering safety assessment.

## Project structure
```text
CivicVisionAI/
├── backend/
│   ├── app/
│   │   ├── api/routes.py
│   │   ├── core/config.py
│   │   ├── db.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── services/
│   ├── tests/
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── .github/workflows/ci.yml
├── Dockerfile.backend
├── Dockerfile.frontend
└── docker-compose.yml
```
