from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Literal
import os

class BaseConfig(BaseSettings):
    """
    Base system settings configuration shared across environments.
    """
    PROJECT_NAME: str = "AegisAI Enterprise Backend"
    API_V1_STR: str = "/api/v1"
    
    # Environment flag: 'dev' | 'prod' | 'test'
    ENVIRONMENT: Literal["dev", "prod", "test"] = Field(default="dev", env="ENVIRONMENT")

    # Security keys
    SECRET_KEY: str = Field(default="SUPER_SECRET_AEGIS_KEY_2026_CHANGE_ME", env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # PostgreSQL config
    POSTGRES_SERVER: str = Field(default="localhost", env="POSTGRES_SERVER")
    POSTGRES_USER: str = Field(default="postgres", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(default="postgres", env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(default="aegisai", env="POSTGRES_DB")
    POSTGRES_PORT: str = Field(default="5432", env="POSTGRES_PORT")
    DATABASE_URL: Optional[str] = None

    # Redis config
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    
    # Qdrant config
    QDRANT_HOST: str = Field(default="localhost", env="QDRANT_HOST")
    QDRANT_PORT: int = Field(default=6333, env="QDRANT_PORT")
    QDRANT_API_KEY: Optional[str] = Field(default=None, env="QDRANT_API_KEY")

    # LLM Keys & Settings
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    GEMINI_API_KEY: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    DEFAULT_AI_PROVIDER: str = Field(default="openai", env="DEFAULT_AI_PROVIDER")
    DEFAULT_AI_MODEL: str = Field(default="gpt-4o-mini", env="DEFAULT_AI_MODEL")

    class Config:
        case_sensitive = True
        env_file = ".env"

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

class DevelopmentConfig(BaseConfig):
    ENVIRONMENT: str = "dev"

class ProductionConfig(BaseConfig):
    ENVIRONMENT: str = "prod"
    # Overwrite settings to strictly enforce TLS in production
    class Config:
        env_file = ".env.prod"

class TestConfig(BaseConfig):
    ENVIRONMENT: str = "test"
    POSTGRES_DB: str = "aegisai_test"
    class Config:
        env_file = ".env.test"

def get_settings() -> BaseConfig:
    """
    Resolve the correct settings profile based on the active ENVIRONMENT variable.
    """
    env = os.getenv("ENVIRONMENT", "dev").lower()
    if env == "prod":
        return ProductionConfig()
    elif env == "test":
        return TestConfig()
    return DevelopmentConfig()

settings = get_settings()
