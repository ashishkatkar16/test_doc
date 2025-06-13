import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache
from pydantic import Extra


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Environment
    debug: bool = False
    environment: str = "development"

    # Database
    database_url: str
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "docuprocess"
    database_user: str = "postgres"
    database_password: str = "postgres"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    celery_task_always_eager: bool = False
    celery_task_eager_propagates: bool = False

    # File Paths
    robot_folder_path: str = "./robot_folder"
    processed_folder_path: str = "./processed"
    log_folder_path: str = "./logs"

    # Email Configuration
    smtp_server: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = "cloudwisedk@gmail.com"
    smtp_password: str = "cloudwiseDK@@2025"
    smtp_use_tls: bool = True
    email_from: str = "noreply@gmail.com"
    email_to_default: str = "cloudwisedk@gmail.com"
    email_cc: Optional[str] = None

    # API Configuration
    main_api_host: str = "0.0.0.0"
    main_api_port: int = 8000
    analysis_api_port: int = 8001
    email_api_port: int = 8002
    rpa_api_port: int = 8003

    # OCR Configuration
    tesseract_cmd: str = "/usr/bin/tesseract"
    ocr_language: str = "eng"

    # Scoring Thresholds
    auto_approve_threshold: float = 8.0
    quick_review_threshold: float = 4.0
    manual_review_threshold: float = 0.0

    # Security
    secret_key: str = "your-secret-key-here"
    jwt_secret_key: str = "your-jwt-secret-key-here"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Monitoring
    health_check_interval: int = 300
    metrics_enabled: bool = False
    sentry_dsn: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = Extra.ignore


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()