from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "CivicVision API"
    environment: str = "development"
    database_url: str = "sqlite:///./civicvision.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,https://civicvision-ai-mocha.vercel.app"
    upload_dir: str = "./uploads"
    max_upload_mb: int = 8
    model_path: str = ""
    demo_mode: bool = True
    duplicate_radius_km: float = 0.15
    duplicate_window_days: int = 90
    authority_users: str = ""
    auth_token_secret: str = ""
    auth_token_ttl_minutes: int = 480
    auto_migrate: bool = True
    max_image_pixels: int = 25_000_000
    model_version: str = "unversioned"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        configured = [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip() and origin.strip() != "*"]
        # Keep the current production UI origin allowed even when a local .env overrides defaults.
        origins = dict.fromkeys([*configured, "https://civicvision-ai-mocha.vercel.app"])
        return list(origins)

@lru_cache
def get_settings() -> Settings:
    return Settings()
