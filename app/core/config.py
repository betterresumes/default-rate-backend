"""
Production configuration settings for AWS deployment
"""
import os
import boto3
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def get_parameter_store_value(parameter_name: str, default_value: str = "") -> str:
    """Get value from AWS Systems Manager Parameter Store with improved error handling."""
    
    # Extract environment variable name from parameter path
    env_var_name = parameter_name.replace("/accunode/", "").replace("/", "_").upper()
    
    # Always try environment variable first (works in all environments)
    env_value = os.getenv(env_var_name)
    if env_value:
        logger.info(f"✅ Using environment variable {env_var_name}")
        return env_value
    
    # Try legacy DATABASE_URL for backward compatibility
    if "database" in parameter_name.lower():
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            logger.info("✅ Using DATABASE_URL environment variable")
            return database_url
    
    try:
        # Only use Parameter Store if explicitly configured and in AWS
        aws_region = os.getenv("AWS_REGION")
        use_parameter_store = os.getenv("USE_PARAMETER_STORE", "false").lower() == "true"
        
        if aws_region and use_parameter_store:
            logger.info(f"🔍 Attempting to fetch {parameter_name} from Parameter Store...")
            ssm = boto3.client('ssm', region_name=aws_region)
            response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
            logger.info(f"✅ Successfully retrieved {parameter_name} from Parameter Store")
            return response['Parameter']['Value']
        else:
            logger.info(f"⚠️ Parameter Store not configured (AWS_REGION: {aws_region}, USE_PARAMETER_STORE: {use_parameter_store})")
            
    except Exception as e:
        logger.error(f"❌ Failed to get parameter {parameter_name} from Parameter Store: {e}")
        logger.info("📋 Available environment variables:")
        for key in sorted(os.environ.keys()):
            if any(keyword in key.lower() for keyword in ['database', 'redis', 'secret']):
                logger.info(f"   {key}: {'***' if 'secret' in key.lower() or 'password' in key.lower() else os.environ[key]}")
    
    # Final fallback
    if default_value:
        logger.warning(f"⚠️ Using default value for {parameter_name}")
        return default_value
    
    logger.error(f"❌ No value found for {parameter_name}")
    return ""

class Config:
    """Base configuration with AWS Parameter Store support."""
    APP_NAME: str = "AccuNode API"  # Updated app name
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    TESTING: bool = False
    
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # AWS-compatible database URL with Parameter Store fallback
    DATABASE_URL: str = get_parameter_store_value("/accunode/database-url", os.getenv("DATABASE_URL", ""))
    
    # Redis Configuration
    REDIS_URL: str = get_parameter_store_value("/accunode/redis-url", os.getenv("REDIS_URL", "redis://localhost:6379"))
    
    # Security Configuration
    SECRET_KEY: str = get_parameter_store_value("/accunode/secrets/secret-key", os.getenv("SECRET_KEY", "your-secret-key-change-in-production"))
    JWT_SECRET: str = get_parameter_store_value("/accunode/jwt-secret", os.getenv("JWT_SECRET", "your-jwt-secret-change-in-production"))
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
    
        # Celery Configuration (Redis)
    CELERY_BROKER_URL: str = get_parameter_store_value("/accunode/celery-broker-url", os.getenv("CELERY_BROKER_URL", ""))
    CELERY_RESULT_BACKEND: str = get_parameter_store_value("/accunode/celery-result-backend", os.getenv("CELERY_RESULT_BACKEND", ""))
    
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
