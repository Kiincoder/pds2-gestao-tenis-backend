from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    db_host: str = "127.0.0.1"
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_database: str = "clube_tenis"
    db_username: str = "clube"
    db_password: SecretStr = SecretStr("clube_local")
    registration_rate_limit: int = Field(default=5, ge=1)
    registration_rate_window_seconds: int = Field(default=60, ge=1)
    login_rate_limit: int = Field(default=10, ge=1)
    login_rate_window_seconds: int = Field(default=60, ge=1)
    access_token_ttl_minutes: int = Field(default=60, ge=1, le=1440)

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.db_username,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_database,
        )
