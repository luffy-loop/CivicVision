from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.core.config import get_settings
from app.db import Base, engine
from app.api.routes import router

settings = get_settings()
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Community road-condition reporting and computer-vision assistance. Predictions require human verification.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(router)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

@app.get("/")
def root():
    return {"name": settings.app_name, "docs": "/docs", "health": "/api/health"}

@app.get("/api/ready")
def readiness():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database readiness check failed.") from exc
    return {"status": "ready", "database": "ok"}
