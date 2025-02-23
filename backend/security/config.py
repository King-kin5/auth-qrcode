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
    ALGORITHM: str = "HS256"
    
    # Security settings
    MAX_LOGIN_ATTEMPTS: int = Field(5, ge=3, le=10)
    LOGIN_ATTEMPT_WINDOW: int = Field(15, ge=5, le=30)
    PASSWORD_RESET_TOKEN_EXPIRE: int = Field(60, ge=15, le=120)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, ge=5, le=60)
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Initial admin settings
    INITIAL_ADMIN_EMAIL: EmailStr
    INITIAL_ADMIN_PASSWORD: SecretStr
    INITIAL_ADMIN_NAME: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
        case_sensitive=True
    )

    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment setting"""
        allowed = {'development', 'testing', 'production'}
        if v not in allowed:
            raise ValueError(f'Environment must be one of: {", ".join(allowed)}')
        return v

@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance"""
    return Settings()

# Create settings instance
settings = get_settings()