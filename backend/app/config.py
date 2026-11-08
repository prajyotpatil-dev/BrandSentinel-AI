"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path


class Settings(BaseSettings):
    """Environment-based configuration."""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"

    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemma-4-31b-it:free"

    port: int = 8000

    cors_origins: str = "*"

    database_url: str = "sqlite:///./brandsentinel.sqlite"
    # Document Storage Configuration
    storage_backend: str = "local"  # local or cloudinary

    # Cloudinary Configuration
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    # File Upload Configuration
    upload_storage_root: str = "./uploads"
    upload_max_size_mb: int = 10
    upload_allowed_extensions: str = ".pdf,.docx,.doc,.txt"
    upload_allowed_mimetypes: str = (
        "application/pdf,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "application/msword,"
        "text/plain"
    )

    # Vector Store / Evidence Retrieval
    vector_min_similarity: float = 0.05
    vector_top_k: int = 5

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if self.cors_origins.strip() == "*":
            return ["*"]

        return [
            origin.strip().rstrip("/")
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def upload_max_size_bytes(self) -> int:
        return self.upload_max_size_mb * 1024 * 1024

    @property
    def upload_allowed_extensions_list(self) -> List[str]:
        return [
            ext.strip().lower()
            for ext in self.upload_allowed_extensions.split(",")
        ]

    @property
    def upload_allowed_mimetypes_list(self) -> List[str]:
        return [
            mime.strip().lower()
            for mime in self.upload_allowed_mimetypes.split(",")
        ]

    @property
    def upload_storage_path(self) -> Path:
        return Path(self.upload_storage_root)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()