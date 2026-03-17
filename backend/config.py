"""
Configuration management for NBFC Loan Platform
Loads environment variables and provides centralized config access
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # MongoDB Configuration
    MONGODB_URI: str = "mongodb://localhost:27017/nbfc_loan_platform"
    MONGODB_DB_NAME: str = "nbfc_loan_platform"
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"
    
    # JWT Configuration
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24
    
    # Groq LLM Configuration
    GROQ_API_KEY: str = ""
    
    # Encryption Configuration
    ENCRYPTION_KEY: str = ""
    
    # Application URLs
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # OTP Configuration
    OTP_EXPIRY_MINUTES: int = 5
    OTP_MAX_ATTEMPTS: int = 3
    
    # Rate Limiting
    RATE_LIMIT_OTP_PER_15MIN: int = 3
    
    # CORS Origins
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Email / SMTP Configuration
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False

    # Email / Resend Configuration
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = ""
    RESEND_API_BASE_URL: str = "https://api.resend.com"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.ENVIRONMENT.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.ENVIRONMENT.lower() == "production"
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True


# Global settings instance
settings = Settings()


# Directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POLICIES_DIR = os.path.join(BASE_DIR, "policies")
MOCK_DATA_DIR = os.path.join(BASE_DIR, "mock_data")
SANCTION_LETTERS_DIR = os.path.join(BASE_DIR, "sanction_letters")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Ensure directories exist
for directory in [SANCTION_LETTERS_DIR, LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)
