from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Literal, Dict
import os

class BaseConfig(BaseSettings):
    """
    Base system settings configuration shared across environments.
    """
    PROJECT_NAME: str = "AegisAI Enterprise Backend"
    VERSION: str = Field(default="1.0.0", env="APP_VERSION")
    GIT_COMMIT_SHA: str = Field(default="unknown", env="GIT_COMMIT_SHA")
    BUILD_TIMESTAMP: str = Field(default="", env="BUILD_TIMESTAMP")
    API_V1_STR: str = "/api/v1"
    
    # Environment flag: 'dev' | 'prod' | 'test' | 'staging'
    ENVIRONMENT: Literal["dev", "prod", "test", "staging"] = Field(default="dev", env="ENVIRONMENT")

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

    # Database Connection Pool Settings
    DB_POOL_SIZE: int = Field(default=20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=10, env="DB_MAX_OVERFLOW")
    DB_POOL_TIMEOUT: int = Field(default=30, env="DB_POOL_TIMEOUT")
    DB_POOL_RECYCLE: int = Field(default=1800, env="DB_POOL_RECYCLE")
    DB_POOL_PRE_PING: bool = Field(default=True, env="DB_POOL_PRE_PING")
    DB_CONNECT_TIMEOUT: int = Field(default=10, env="DB_CONNECT_TIMEOUT")

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

    # Worker & Scheduling Settings
    WORKER_CONCURRENCY: int = Field(default=10, env="WORKER_CONCURRENCY")
    MAX_TENANT_CONCURRENCY: int = Field(default=5, env="MAX_TENANT_CONCURRENCY")
    WORKER_HEARTBEAT_INTERVAL_SECONDS: int = Field(default=10, env="WORKER_HEARTBEAT_INTERVAL_SECONDS")
    WORKER_STALE_TIMEOUT_SECONDS: int = Field(default=60, env="WORKER_STALE_TIMEOUT_SECONDS")
    WORKER_SHUTDOWN_TIMEOUT_SECONDS: int = Field(default=30, env="WORKER_SHUTDOWN_TIMEOUT_SECONDS")
    SCHEDULER_POLL_INTERVAL_SECONDS: int = Field(default=5, env="SCHEDULER_POLL_INTERVAL_SECONDS")
    SCHEDULER_LEADER_TTL_SECONDS: int = Field(default=15, env="SCHEDULER_LEADER_TTL_SECONDS")
    JOB_MAX_RETRIES: int = Field(default=3, env="JOB_MAX_RETRIES")
    JOB_BASE_BACKOFF_SECONDS: int = Field(default=2, env="JOB_BASE_BACKOFF_SECONDS")
    # Observability & Logging Settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    LOG_FILE_PATH: Optional[str] = Field(default="logs/aegis.log", env="LOG_FILE_PATH")
    LOG_ROTATION: str = Field(default="100 MB", env="LOG_ROTATION")
    LOG_RETENTION: str = Field(default="10 days", env="LOG_RETENTION")
    METRICS_ENABLED: bool = Field(default=True, env="METRICS_ENABLED")
    METRICS_MAX_HISTORY_SECONDS: int = Field(default=86400, env="METRICS_MAX_HISTORY_SECONDS")
    ALERT_ERROR_RATE_THRESHOLD: float = Field(default=0.05, env="ALERT_ERROR_RATE_THRESHOLD")
    ALERT_QUEUE_DEPTH_THRESHOLD: int = Field(default=100, env="ALERT_QUEUE_DEPTH_THRESHOLD")
    ALERT_STALE_WORKER_THRESHOLD_SECONDS: int = Field(default=60, env="ALERT_STALE_WORKER_THRESHOLD_SECONDS")

    # API & Web Security Configurations
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000"
    ]
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1", "testserver", "*.aegisai.enterprise"]
    TRUSTED_PROXIES: list[str] = ["127.0.0.1", "::1", "localhost", "172.16.0.0/12", "10.0.0.0/8", "192.168.0.0/16"]
    MAX_REQUEST_BODY_BYTES: int = 10 * 1024 * 1024   # 10 MB limit for JSON / standard requests
    MAX_UPLOAD_BYTES: int = 50 * 1024 * 1024         # 50 MB limit for document uploads
    ENABLE_HSTS: bool = False
    TLS_CERT_PATH: Optional[str] = Field(default=None, env="TLS_CERT_PATH")
    TLS_KEY_PATH: Optional[str] = Field(default=None, env="TLS_KEY_PATH")
    
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

class StagingConfig(BaseConfig):
    ENVIRONMENT: str = "staging"
    ENABLE_HSTS: bool = True
    POSTGRES_DB: str = "aegisai_staging"
    DOCUMENT_STORAGE_PATH: str = "storage/staging"
    class Config:
        env_file = ".env.staging"

class ProductionConfig(BaseConfig):
    ENVIRONMENT: str = "prod"
    ENABLE_HSTS: bool = True
    class Config:
        env_file = ".env.prod"

class TestConfig(BaseConfig):
    __test__ = False
    ENVIRONMENT: str = "test"
    POSTGRES_DB: str = "aegisai_test"
    class Config:
        env_file = ".env.test"

def validate_production_configuration(cfg: BaseConfig) -> list[str]:
    """
    Validates production and staging configuration invariants.
    Returns a list of error messages (empty if valid).
    """
    errors = []
    env_name = cfg.ENVIRONMENT
    env_label = "Production" if env_name == "prod" else "Staging"
    if env_name in ["prod", "staging"]:
        # 1. JWT Secret strength and non-default check
        if not cfg.SECRET_KEY or cfg.SECRET_KEY == "SUPER_SECRET_AEGIS_KEY_2026_CHANGE_ME" or "replace-with" in cfg.SECRET_KEY:
            errors.append(f"{env_label} SECRET_KEY must be securely configured and not use default placeholder values.")
        elif len(cfg.SECRET_KEY) < 32:
            errors.append(f"{env_label} SECRET_KEY is too short ({len(cfg.SECRET_KEY)} chars); must be at least 32 characters.")

        # 2. Database credentials & driver verification
        db_url = cfg.get_database_url()
        if db_url.startswith("sqlite"):
            errors.append(f"SQLite database is not permitted in {env_label.lower()} environment. A dedicated PostgreSQL database must be configured.")
        if cfg.POSTGRES_PASSWORD == "postgres" and not cfg.DATABASE_URL:
            errors.append(f"{env_label} POSTGRES_PASSWORD must not use default 'postgres' password.")

        # 3. Database connection pool boundaries
        if cfg.DB_POOL_SIZE < 5:
            errors.append(f"{env_label} DB_POOL_SIZE ({cfg.DB_POOL_SIZE}) is too low; minimum recommended is 5.")
        elif cfg.DB_POOL_SIZE > 100:
            errors.append(f"{env_label} DB_POOL_SIZE ({cfg.DB_POOL_SIZE}) exceeds safe boundary (100); adjust according to PostgreSQL max_connections.")

        # 4. CORS wildcard with credentials check
        if "*" in cfg.CORS_ORIGINS:
            errors.append(f"{env_label} CORS_ORIGINS must not contain wildcard '*' when allow_credentials=True.")

        # 5. Trusted hosts & proxy validation
        if "*" in cfg.ALLOWED_HOSTS:
            errors.append(f"{env_label} ALLOWED_HOSTS must not contain wildcard '*' to protect against Host header attacks.")
        if not cfg.ALLOWED_HOSTS:
            errors.append(f"{env_label} ALLOWED_HOSTS must be explicitly configured.")
        if "*" in getattr(cfg, "TRUSTED_PROXIES", []):
            errors.append(f"{env_label} TRUSTED_PROXIES must not contain wildcard '*' to prevent IP spoofing.")

        # 6. TLS certificate and key consistency
        if cfg.TLS_CERT_PATH and not cfg.TLS_KEY_PATH:
            errors.append("TLS_KEY_PATH must be provided when TLS_CERT_PATH is specified.")
        if cfg.TLS_KEY_PATH and not cfg.TLS_CERT_PATH:
            errors.append("TLS_CERT_PATH must be provided when TLS_KEY_PATH is specified.")

        # 7. Storage directory configuration
        if not cfg.DOCUMENT_STORAGE_PATH:
            errors.append(f"DOCUMENT_STORAGE_PATH must be explicitly configured in {env_label.lower()}.")

        # 8. Environment isolation check (Staging must not point to Production DB)
        if env_name == "staging" and cfg.POSTGRES_DB == "aegisai_prod":
            errors.append("Staging environment must not connect to the production database 'aegisai_prod'.")

    return errors

def get_settings() -> BaseConfig:
    """
    Resolve the correct settings profile based on the active ENVIRONMENT variable.
    """
    env = os.getenv("ENVIRONMENT", "dev").lower()
    if env in ["prod", "production"]:
        return ProductionConfig()
    elif env in ["staging", "stage"]:
        return StagingConfig()
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

