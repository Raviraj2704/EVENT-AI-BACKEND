# ============================================================================
# Configuration Module
# ============================================================================
# File: app/config.py
# Purpose: Environment variable management and validation

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    app_name: str = "EventAI API"
    app_version: str = "1.0.0"
    debug: bool = True
    log_level: str = "INFO"
    
    # Database Setup
    database_url: str
    
    # Security / Auth
    secret_key: str = "fallback-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    
    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    # Tell Pydantic to read from .env and ignore any extra variables it doesn't need yet
    model_config = SettingsConfigDict(
        env_file=".env", 
        extra="ignore", 
        case_sensitive=False
    )

settings = Settings()