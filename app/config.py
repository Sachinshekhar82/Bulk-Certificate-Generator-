import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    APP_NAME: str = "Bulk Certificate Generator API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Base directories
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    STORAGE_DIR: str = "storage/certificates"

    # Database
    DATABASE_URL: str = "sqlite:///./certificates.db"

    # Verification / QR Code Base URL
    BASE_URL: str = "http://localhost:8000"

    # Processing limits
    MAX_BATCH_SIZE: int = 1000
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 200

    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def absolute_storage_dir(self) -> Path:
        """Returns the resolved absolute path to the certificates storage directory."""
        path = Path(self.STORAGE_DIR)
        if not path.is_absolute():
            path = self.BASE_DIR / path
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
