"""
Production configuration settings
"""
import os
from typing import Optional

class Config:
    """Base configuration."""
    APP_NAME: str = "Default Rate Backend API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    TESTING: bool = False
    
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-jwt-secret-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://yourdomain.com"  # Add your frontend domains
    ]
    
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB
    ALLOWED_EXTENSIONS: set = {".xlsx", ".xls", ".csv"}
    
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG: bool = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG: bool = False
    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "WARNING")


class TestingConfig(Config):
    """Testing configuration."""
    TESTING: bool = True
    DEBUG: bool = True


config_mapping = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}

def get_config() -> Config:
    """Get configuration based on environment."""
    env = os.getenv("ENVIRONMENT", "development").lower()
    return config_mapping.get(env, DevelopmentConfig)()
