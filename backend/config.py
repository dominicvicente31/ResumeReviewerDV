from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_hours: int = 24
    refresh_token_expire_days: int = 7
    max_login_attempts: int = 10
    lockout_duration_minutes: int = 15

    # External APIs
    anthropic_api_key: str
    ai_model: str = "claude-sonnet-4-6"

    # CORS / environment
    allowed_origins: str = "http://localhost:3000"
    env: str = "development"

    # File storage
    upload_dir: str = "uploads"

    @field_validator("jwt_secret_key")
    @classmethod
    def jwt_secret_must_be_secure(cls, v: str) -> str:
        insecure = {"change-me-in-production", "secret", "password", ""}
        if v.lower() in insecure or len(v) < 32:
            raise ValueError(
                "JWT_SECRET_KEY is insecure. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


settings = Settings()
