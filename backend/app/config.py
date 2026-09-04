from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TIC Control AI"
    app_env: Literal["development", "production", "test"] = "development"
    secret_key: str = Field(default="cambiar-en-produccion-use-32-bytes-aleatorios")
    database_url: str = "sqlite:///./data/ticcontrol.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    access_token_minutes: int = 15
    refresh_token_days: int = 7
    https_only: bool = False
    cookie_secure: bool = False

    bootstrap_admin_username: str = "admin"
    bootstrap_admin_email: str = "admin@localhost"
    bootstrap_admin_password: str = "CambiarAdmin123!"

    upload_dir: str = "./data/packages"
    max_package_mb: int = 512
    heartbeat_offline_factor: int = 3
    default_heartbeat_seconds: int = 60
    metrics_retention_days: int = 30

    rate_limit_login: str = "5/minute"
    rate_limit_agent: str = "120/minute"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
