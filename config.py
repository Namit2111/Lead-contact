from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Google OAuth settings
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str

    # MongoDB settings
    mongo_uri: str
    mongo_db_name: str

    # Optional settings
    debug: bool = False
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
