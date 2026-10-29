from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    jwt_alg: str = "HS256"
    jwt_expire_minutes: int = 720
    sms_master_psk: str
    cors_origins: str = "http://localhost:5173"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @field_validator("database_url", mode="before")
    @classmethod
    def _ensure_async_driver(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgresql://") and "+asyncpg" not in v:
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()  # type: ignore