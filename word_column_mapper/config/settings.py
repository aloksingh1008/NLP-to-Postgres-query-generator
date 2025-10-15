"""Application settings and configuration management."""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = Field(default="Word Column Mapper")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    
    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    workers: int = Field(default=1)
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_password: Optional[str] = Field(default=None)
    redis_max_connections: int = Field(default=10)
    
    # Cache Configuration
    cache_ttl: int = Field(default=3600)  # 1 hour
    cache_max_size: int = Field(default=10000)
    enable_cache: bool = Field(default=True)
    
    # Search Configuration
    fuzzy_threshold: float = Field(default=0.6)
    max_results: int = Field(default=10)
    max_query_length: int = Field(default=100)
    enable_phonetic: bool = Field(default=False)
    
    # Performance
    max_concurrent_requests: int = Field(default=100)
    request_timeout: int = Field(default=30)
    
    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080", "http://localhost:8000"]
    )
    
    # Security
    secret_key: str = Field(default="your-secret-key-change-in-production")
    api_key_header: str = Field(default="X-API-Key")
    
    # OpenAI (optional, for future features)
    openai_api_key: Optional[str] = Field(default=None)
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra environment variables
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
