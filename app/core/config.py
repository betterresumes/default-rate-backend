"""
Production configuration settings for AWS deployment
"""
import os
import boto3
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def get_parameter_store_value(parameter_name: str, default_value: str = "") -> str:
    """Get value from AWS Systems Manager Parameter Store."""
    try:
        # Only use Parameter Store in AWS environment
        if os.getenv("AWS_REGION") and os.getenv("ENVIRONMENT", "").lower() == "production":
            ssm = boto3.client('ssm', region_name=os.getenv("AWS_REGION", "us-east-1"))
            response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
            return response['Parameter']['Value']
    except Exception as e:
        logger.warning(f"Failed to get parameter {parameter_name} from Parameter Store: {e}")
    
    # Fallback to environment variable or default
    return os.getenv(parameter_name.replace("/accunode/", "").upper(), default_value)

class Config:
    """Base configuration with AWS Parameter Store support."""
    APP_NAME: str = "AccuNode API"  # Updated app name
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    TESTING: bool = False
    
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # AWS-compatible database URL with Parameter Store fallback
    DATABASE_URL: str = get_parameter_store_value("/accunode/database/url", os.getenv("DATABASE_URL", ""))
    
    # Redis URL with ElastiCache support
    REDIS_URL: str = get_parameter_store_value("/accunode/redis/url", os.getenv("REDIS_URL", "redis://localhost:6379"))
    
    # Secure secrets from Parameter Store
    SECRET_KEY: str = get_parameter_store_value("/accunode/secrets/secret_key", os.getenv("SECRET_KEY", "your-secret-key-change-in-production"))
    JWT_SECRET: str = get_parameter_store_value("/accunode/secrets/jwt_secret", os.getenv("JWT_SECRET", "your-jwt-secret-change-in-production"))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # AWS-specific settings
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "accunode-ml-models")
    S3_ML_MODELS_PREFIX: str = "models/"
    
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://api.accunode.ai",  # Add your production domain
        "https://accunode.ai"  # Add your frontend domains
    ]
    
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB
    ALLOWED_EXTENSIONS: set = {".xlsx", ".xls", ".csv"}
    
    # Celery configuration with Redis backend
    CELERY_BROKER_URL: str = get_parameter_store_value("/accunode/celery/broker_url", os.getenv("CELERY_BROKER_URL", ""))
    CELERY_RESULT_BACKEND: str = get_parameter_store_value("/accunode/celery/result_backend", os.getenv("CELERY_RESULT_BACKEND", ""))
    
    # Set broker URLs from REDIS_URL if not explicitly set
    @property
    def celery_broker_url(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL
    
    @property  
    def celery_result_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL
    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Health check configuration
    HEALTH_CHECK_TIMEOUT: int = int(os.getenv("HEALTH_CHECK_TIMEOUT", "5"))
    
    # Auto-scaling configuration
    AUTO_SCALING_ENABLED: bool = os.getenv("AUTO_SCALING_ENABLED", "true").lower() == "true"
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "6"))
    MIN_WORKERS: int = int(os.getenv("MIN_WORKERS", "2"))
    

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
