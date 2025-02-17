

from pydantic import EmailStr, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str
   
    # Application settings
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str
    # Security settings
    MAX_LOGIN_ATTEMPTS: int = Field(5, ge=3, le=10)
    LOGIN_ATTEMPT_WINDOW: int = Field(15, ge=5, le=30)
    PASSWORD_RESET_TOKEN_EXPIRE: int = Field(60, ge=15, le=120)
   

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
        case_sensitive=True
    )


    # Initial admin settings
    INITIAL_ADMIN_EMAIL: EmailStr
    INITIAL_ADMIN_PASSWORD: SecretStr
    INITIAL_ADMIN_NAME: str
@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance"""
    return Settings()
# Create settings instance
settings = get_settings()
