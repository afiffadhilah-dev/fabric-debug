from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from dotenv import load_dotenv

# Load .env file into os.environ BEFORE pydantic reads it
# This ensures ALL environment variables are available to both:
# - pydantic-settings (reads from os.environ)
# - Langfuse SDK (reads from os.environ)
# - Any other libraries that expect env vars
load_dotenv()


class Settings(BaseSettings):
    # LLM Configuration
    LLM_PROVIDER: str = "openrouter"
    LLM_MODEL: str = "openai/gpt-4.1-nano"
    # Resume analyzer specific overrides (if not set, fall back to LLM_PROVIDER / LLM_MODEL)
    RESUME_ANALYZER_PROVIDER: str = "openrouter"
    RESUME_ANALYZER_MODEL: str = "google/gemini-2.5-flash"
    
    # Multi-model configuration for different tasks
    LLM_FAST_MODEL: str = "openai/gpt-4.1-nano"  # Fast extraction
    LLM_DEEP_MODEL: str = "openai/gpt-4.1-nano"  # Deep analysis (change to better model when available)

    # OpenRouter
    OPENROUTER_API_KEY: Optional[str] = None

    # Gemini
    GEMINI_API_KEY: Optional[str] = None

    # DeepSeek
    DEEPSEEK_API_KEY: Optional[str] = None

    # Other
    USE_LLM_QUEUE: bool = False
    GEMINI_MAX_RPM: int = 10

    # Optional app/server/database fields (in.env)
    DATABASE_URL: Optional[str] = None
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000

    # API Security
    API_SECRET_KEY: Optional[str] = None

    # Langfuse Observability
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"
    LANGFUSE_ENABLED: bool = False

    # Checkpointer: "memory" (no DB connections) or "postgres" (persistent state)
    # Use "memory" for Supabase free tier to avoid connection pool exhaustion
    # See docs/supabase-502-investigation.md
    CHECKPOINTER_TYPE: str = "memory"

    # Auto-trigger summarization when interview completes
    # Disable on Supabase free tier to avoid connection pool exhaustion
    AUTO_SUMMARIZE: bool = False

    # DISABLED: Redis & Celery Configuration (no Redis on Render)
    # REDIS_URL: str = "redis://localhost:6379/0"
    # CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    # CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # pydantic-settings v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # ignore unknown env vars instead of raising errors
    )

    EMBEDDING_MODEL: str = "openai/text-embedding-3-small"

    ANALYZE_RESUME_BATCH_SIZE: int = 10  # Number of questions to analyze against resume in a single batch
    MAX_WORKER_THREADS: int = 4  # Max threads for concurrent LLM calls (e.g. in batch analysis)


settings = Settings()
