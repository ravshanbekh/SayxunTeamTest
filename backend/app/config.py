"""
Application configuration using Pydantic Settings.
Loads environment variables from .env file or Railway environment.
"""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database - Railway provides DATABASE_URL automatically
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # File paths
    UPLOAD_DIR: str = "uploads"
    EXPORT_DIR: str = "exports"
    
    # Session
    SESSION_DURATION_MINUTES: int = 90
    
    # To'lovlar: tasdiq/rad haqida talabaga bot orqali xabar yuborish uchun (ixtiyoriy)
    BOT_TOKEN: Optional[str] = None
    # Testga bog'lanmagan cheklar ko'rib chiqilgandan keyin necha kun saqlanadi
    RECEIPT_RETENTION_DAYS: int = 7
    
    # Rasch: T-ballni yuqoridan cheklash (bo'sh - cheklanmaydi, masalan 75)
    RASCH_MAX_SCORE: Optional[float] = None

    @field_validator("RASCH_MAX_SCORE", mode="before")
    @classmethod
    def _empty_as_none(cls, value):
        # docker-compose bo'sh qiymatni "" sifatida uzatadi
        return None if value in ("", None) else value
    
    # CORS - Railway deployment
    CORS_ORIGINS: str = "*"
    
    # Port - Railway provides this
    PORT: int = int(os.getenv("PORT", 8000))
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Ignore extra Railway env vars
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


# Global settings instance
settings = Settings()
