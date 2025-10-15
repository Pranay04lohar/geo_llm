"""
Configuration management for Dynamic RAG System.
Handles environment variables, Redis settings, and system parameters.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional, List, Any
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_password: Optional[str] = None
    redis_max_connections: int = 10
    
    # File Upload Settings
    max_file_size_mb: int = 100
    max_files_per_request: int = 2
    max_files_per_user_per_day: int = 20
    
    # Session Management
    session_ttl_hours: int = 1
    quota_ttl_hours: int = 24
    
    # Embedding Settings
    embedding_model: str = "all-MiniLM-L6-v2"
    use_gpu: bool = True
    batch_size: int = 32
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 50
    
    # FAISS Settings
    faiss_index_type: str = "IndexFlatIP"  # Inner Product for cosine similarity
    embedding_dimension: int = 384  # all-MiniLM-L6-v2 dimension
    
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    allowed_file_types: List[str] = Field(default_factory=lambda: [".pdf", ".txt", ".docx", ".md"]) 

    # Pydantic v2 settings config
    model_config = SettingsConfigDict(
        env_file = ".env",
        case_sensitive = False,
        env_nested_delimiter = '__'
    )

    # Allow comma-separated env var for list parsing
    @field_validator("allowed_file_types", mode="before")
    @classmethod
    def parse_allowed_file_types(cls, v: Any) -> Any:
        if isinstance(v, str):
            parts = [p.strip() for p in v.split(',') if p.strip()]
            return parts
        return v


# Global settings instance
settings = Settings()


# Redis connection configuration
REDIS_CONFIG = {
    "url": settings.redis_url,
    "password": settings.redis_password,
    "max_connections": settings.redis_max_connections,
    "retry_on_timeout": True,
    "decode_responses": True
}


# File processing configuration
FILE_PROCESSING_CONFIG = {
    "max_size_bytes": settings.max_file_size_mb * 1024 * 1024,
    "allowed_extensions": settings.allowed_file_types,
    "chunk_size": settings.chunk_size_tokens,
    "chunk_overlap": settings.chunk_overlap_tokens
}


# Embedding configuration
EMBEDDING_CONFIG = {
    "model_name": settings.embedding_model,
    "use_gpu": settings.use_gpu,
    "batch_size": settings.batch_size,
    "dimension": settings.embedding_dimension
}


# Session configuration
SESSION_CONFIG = {
    "ttl_seconds": settings.session_ttl_hours * 3600,
    "quota_ttl_seconds": settings.quota_ttl_hours * 3600,
    "max_files_per_user": settings.max_files_per_user_per_day
}


def get_redis_key_user_quota(user_id: str) -> str:
    """Generate Redis key for user quota tracking."""
    return f"user:{user_id}:upload_count"


def get_redis_key_session_metadata(session_id: str) -> str:
    """Generate Redis key for session metadata."""
    return f"session:{session_id}:metadata"


def get_redis_key_session_ttl(session_id: str) -> str:
    """Generate Redis key for session TTL tracking."""
    return f"session:{session_id}:ttl"
