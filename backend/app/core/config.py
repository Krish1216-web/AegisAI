from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Literal, Dict
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
    RATE_LIMIT_RPM: int = Field(default=60, env="RATE_LIMIT_RPM")
    
    # Real Integration Settings
    TAVILY_API_KEY: Optional[str] = Field(default=None, env="TAVILY_API_KEY")
    MEMORY_PROVIDER: str = Field(default="mock", env="MEMORY_PROVIDER")
    RESEARCH_PROVIDER: str = Field(default="mock", env="RESEARCH_PROVIDER")
    EMBEDDING_PROVIDER: str = Field(default="openai", env="EMBEDDING_PROVIDER")
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", env="EMBEDDING_MODEL")
    EMBEDDING_DIMENSION: int = Field(default=1536, env="EMBEDDING_DIMENSION")
    EMBEDDING_BATCH_SIZE: int = Field(default=32, env="EMBEDDING_BATCH_SIZE")
    CHUNK_SIZE: int = Field(default=1000, env="CHUNK_SIZE")
    CHUNK_OVERLAP: int = Field(default=150, env="CHUNK_OVERLAP")
    DOCUMENT_STORAGE_PATH: str = Field(default="storage", env="DOCUMENT_STORAGE_PATH")
    MAX_DOCUMENT_SIZE_MB: int = Field(default=50, env="MAX_DOCUMENT_SIZE_MB")
    
    MODEL_PRICING: Dict[str, Dict[str, Dict[str, float]]] = {
        "openai": {
            "gpt-4o": {"input": 5.0, "output": 15.0},
            "gpt-4o-mini": {"input": 0.150, "output": 0.600},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        },
        "gemini": {
            "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
            "gemini-1.5-flash": {"input": 0.075, "output": 0.300},
        },
        "anthropic": {
            "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
            "claude-3-haiku": {"input": 0.25, "output": 1.25},
        }
    }

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

def calculate_model_cost(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> Dict[str, Optional[float]]:
    try:
        pricing = settings.MODEL_PRICING.get(provider.lower())
        if not pricing:
            return {"input_cost": None, "output_cost": None, "total_cost": None}
            
        model_pricing = pricing.get(model.lower())
        if not model_pricing:
            found_model = None
            for key in pricing:
                if key in model.lower():
                    found_model = key
                    break
            if found_model:
                model_pricing = pricing[found_model]
            else:
                return {"input_cost": None, "output_cost": None, "total_cost": None}
                
        input_rate = model_pricing["input"] / 1_000_000
        output_rate = model_pricing["output"] / 1_000_000
        
        input_cost = prompt_tokens * input_rate
        output_cost = completion_tokens * output_rate
        total_cost = input_cost + output_cost
        
        return {
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(total_cost, 6)
        }
    except Exception:
        return {"input_cost": None, "output_cost": None, "total_cost": None}

