from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl

class Settings(BaseSettings):
    DATABASE_URL: str     
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM: str | None = None
    FRONTEND_RESET_URL: str | None = None

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

settings = Settings()
