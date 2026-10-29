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

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()  # type: ignore