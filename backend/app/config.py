"""
Unified Configuration for GeoLLM Monolithic Backend

This module consolidates all service configurations into a single place.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    """Unified settings for all services"""
    
    # ============================================================================
    # API Keys
    # ============================================================================
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    
    # ============================================================================
    # LLM Model Configuration
    # ============================================================================
    NER_MODEL: str = os.getenv("NER_MODEL", "openai/gpt-oss-20b:free")
    INTENT_MODEL: str = os.getenv("INTENT_MODEL", "openai/gpt-oss-20b:free")
    RESPONSE_MODEL: str = os.getenv("RESPONSE_MODEL", "openai/gpt-oss-20b:free")
    
    # ============================================================================
    # Redis Configuration (for RAG)
    # ============================================================================
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    
    # ============================================================================
    # RAG Service Configuration
    # ============================================================================
    USE_GPU: bool = os.getenv("USE_GPU", "false").lower() == "true"
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    TOP_K: int = int(os.getenv("TOP_K", "5"))
    
    # Session management
    SESSION_TTL: int = int(os.getenv("SESSION_TTL", "3600"))  # 1 hour
    MAX_SESSIONS: int = int(os.getenv("MAX_SESSIONS", "100"))
    
    # ============================================================================
    # Google Earth Engine Configuration
    # ============================================================================
    GEE_PROJECT: str = os.getenv("GEE_PROJECT", "")
    GEE_SERVICE_ACCOUNT: Optional[str] = os.getenv("GEE_SERVICE_ACCOUNT")
    GEE_PRIVATE_KEY_PATH: Optional[str] = os.getenv("GEE_PRIVATE_KEY_PATH")
    
    # ============================================================================
    # Search Service Configuration
    # ============================================================================
    NOMINATIM_URL: str = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org")
    SEARCH_TIMEOUT: int = int(os.getenv("SEARCH_TIMEOUT", "60"))
    
    # ============================================================================
    # Application Settings
    # ============================================================================
    APP_NAME: str = "GeoLLM Monolithic Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # CORS
    CORS_ORIGINS: list = ["*"]  # Configure appropriately for production
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance"""
    return settings


def get_openrouter_config() -> dict:
    """Get OpenRouter configuration for LLM models"""
    return {
        "api_key": settings.OPENROUTER_API_KEY,
        "ner_model": settings.NER_MODEL,
        "intent_model": settings.INTENT_MODEL,
        "response_model": settings.RESPONSE_MODEL,
    }


def get_redis_config() -> dict:
    """Get Redis configuration"""
    return {
        "url": settings.REDIS_URL,
        "host": settings.REDIS_HOST,
        "port": settings.REDIS_PORT,
        "db": settings.REDIS_DB,
        "password": settings.REDIS_PASSWORD,
    }


def get_rag_config() -> dict:
    """Get RAG service configuration"""
    return {
        "use_gpu": settings.USE_GPU,
        "embedding_model": settings.EMBEDDING_MODEL,
        "chunk_size": settings.CHUNK_SIZE,
        "chunk_overlap": settings.CHUNK_OVERLAP,
        "top_k": settings.TOP_K,
        "session_ttl": settings.SESSION_TTL,
        "max_sessions": settings.MAX_SESSIONS,
    }


def get_gee_config() -> dict:
    """Get Google Earth Engine configuration"""
    return {
        "project": settings.GEE_PROJECT,
        "service_account": settings.GEE_SERVICE_ACCOUNT,
        "private_key_path": settings.GEE_PRIVATE_KEY_PATH,
    }


# ============================================================================
# RAG Service Constants (for compatibility with RAGStore)
# ============================================================================

# Redis connection configuration
REDIS_CONFIG = {
    "url": settings.REDIS_URL,
    "password": settings.REDIS_PASSWORD,
    "max_connections": 10,
    "retry_on_timeout": True,
    "decode_responses": True
}

# File processing configuration
FILE_PROCESSING_CONFIG = {
    "max_size_bytes": 100 * 1024 * 1024,  # 100 MB
    "allowed_extensions": [".pdf", ".txt", ".docx", ".md"],
    "chunk_size": settings.CHUNK_SIZE,
    "chunk_overlap": settings.CHUNK_OVERLAP
}

# Embedding configuration  
EMBEDDING_CONFIG = {
    "model_name": settings.EMBEDDING_MODEL,
    "use_gpu": settings.USE_GPU,
    "batch_size": 32,
    "dimension": 384  # all-MiniLM-L6-v2 dimension
}

# Session configuration
SESSION_CONFIG = {
    "ttl_seconds": settings.SESSION_TTL,
    "quota_ttl_seconds": 86400,  # 24 hours
    "max_files_per_user": 20
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

