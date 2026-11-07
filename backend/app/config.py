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

    # File Upload Configuration
    upload_storage_root: str = "./uploads"
    upload_max_size_mb: int = 10
    upload_allowed_extensions: str = ".pdf,.docx,.doc,.txt"
    upload_allowed_mimetypes: str = "application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/msword,text/plain"

    # Vector Store / Evidence Retrieval Configuration
    # Minimum cosine similarity for a result to be included (inclusive).
    # Raising this increases precision at the cost of recall.
    vector_min_similarity: float = 0.05
    # Default number of results returned by search_evidence().
    vector_top_k: int = 5

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def upload_max_size_bytes(self) -> int:
        """Convert MB to bytes."""
        return self.upload_max_size_mb * 1024 * 1024

    @property
    def upload_allowed_extensions_list(self) -> List[str]:
        """Parse allowed extensions."""
        return [ext.strip().lower() for ext in self.upload_allowed_extensions.split(",")]

    @property
    def upload_allowed_mimetypes_list(self) -> List[str]:
        """Parse allowed MIME types."""
        return [mime.strip().lower() for mime in self.upload_allowed_mimetypes.split(",")]

    @property
    def upload_storage_path(self) -> Path:
        """Get storage path as Path object."""
        return Path(self.upload_storage_root)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
