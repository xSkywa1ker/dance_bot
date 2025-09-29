from functools import lru_cache
import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    env: str = Field(default="dev", alias="ENV")
    timezone: str = Field(default="Europe/Moscow", alias="TIMEZONE")

    postgres_db: str = Field(default="dance", alias="POSTGRES_DB")
    postgres_user: str = Field(default="dance", alias="POSTGRES_USER")
    postgres_password: str = Field(default="dance", alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")

    jwt_secret: str = Field(default="secret", alias="JWT_SECRET")
    jwt_expire_min: int = Field(default=43200, alias="JWT_EXPIRE_MIN")

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_admin_ids: str = Field(default="", alias="TELEGRAM_ADMIN_IDS")
    bot_api_token: str = Field(default="", alias="BOT_API_TOKEN")

    payment_provider: str = Field(default="stub", alias="PAYMENT_PROVIDER")
    payment_return_url: str = Field(default="http://localhost", alias="PAYMENT_RETURN_URL")
    payment_webhook_secret: str = Field(default="", alias="PAYMENT_WEBHOOK_SECRET")
    payment_api_key: str = Field(default="", alias="PAYMENT_API_KEY")
    payment_api_secret: str = Field(default="", alias="PAYMENT_API_SECRET")

    default_admin_login: str = Field(default="admin", alias="DEFAULT_ADMIN_LOGIN")
    default_admin_password: str = Field(default="admin123", alias="DEFAULT_ADMIN_PASSWORD")

    google_sheets_enabled: bool = Field(default=False, alias="GOOGLE_SHEETS_ENABLED")
    google_service_account_json_path: str = Field(
        default="", alias="GOOGLE_SERVICE_ACCOUNT_JSON_PATH"
    )

    class Config:
        populate_by_name = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(**os.environ)
