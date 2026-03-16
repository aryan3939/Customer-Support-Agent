"""
Configuration management for the Customer Support Agent.

WHY THIS FILE EXISTS:
---------------------
Every application needs settings (database URLs, API keys, feature flags).
Hardcoding these is dangerous (secrets in code) and inflexible (can't change
without redeploying). This file:

1. Reads settings from .env file (or environment variables)
2. Validates them at startup (fails fast if something is missing)
3. Provides typed access (IDE autocomplete, no typos)
4. Centralizes ALL configuration in one place

HOW IT WORKS:
-------------
Pydantic Settings reads from environment variables (and .env files):

    .env file:  DATABASE_URL=postgresql+asyncpg://...
                       ↓
    Python:     settings.DATABASE_URL  →  "postgresql+asyncpg://..."

If a required variable is missing, the app crashes immediately with a clear
error message — much better than crashing 10 minutes later with a confusing one.
"""

from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env into os.environ BEFORE anything else.
# Pydantic Settings only reads .env into its own fields — it does NOT set
# os.environ. LangChain/LangSmith SDK reads LANGCHAIN_* vars directly from
# os.environ, so we need load_dotenv() to make them visible.
load_dotenv()


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables / .env file.
    
    Each field maps to an environment variable with the SAME NAME.
    For example:
        APP_NAME in .env  →  self.APP_NAME in Python
    
    Fields with default values are optional in .env.
    Fields without defaults are REQUIRED — app won't start without them.
    """
    
    # ==========================================================================
    # Model Config — tells Pydantic HOW to load settings
    # ==========================================================================
    model_config = SettingsConfigDict(
        env_file=".env",           # Load from .env file in project root
        env_file_encoding="utf-8", # Handle special characters
        case_sensitive=False,      # DATABASE_URL = database_url = DataBase_Url
        extra="ignore",            # Don't crash on unknown variables in .env
    )
    
    # ==========================================================================
    # Application Settings
    # ==========================================================================
    APP_NAME: str = "Customer Support Agent"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    
    # ==========================================================================
    # Database (Supabase PostgreSQL)
    # ==========================================================================
    # REQUIRED — app won't start without this
    DATABASE_URL: str
    
    # Optional Supabase direct API access
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    
    # ==========================================================================
    # Redis (Optional — for caching)
    # ==========================================================================
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # ==========================================================================
    # LLM Configuration
    # ==========================================================================
    LLM_PROVIDER: Literal["google", "groq"] = "google"
    
    # API Keys — at least one must be provided based on LLM_PROVIDER
    GOOGLE_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    
    # Model settings
    LLM_MODEL: str = "gemini-2.0-flash"
    LLM_TEMPERATURE: float = Field(default=0.3, ge=0.0, le=1.0)
    
    # ==========================================================================
    # LangSmith (Tracing & Observability)
    # ==========================================================================
    LANGCHAIN_TRACING_V2: bool = True  # Set to True to enable tracing
    LANGCHAIN_API_KEY: str = ""         # Get from smith.langchain.com
    LANGCHAIN_PROJECT: str = "customer-support-agent"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    
    # ==========================================================================
    # Embeddings
    # ==========================================================================
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # ==========================================================================
    # Security
    # ==========================================================================
    JWT_SECRET: str = "change-this-in-production"
    API_KEY_SALT: str = "change-this-too"
    SUPABASE_JWT_SECRET: str = ""  # From Supabase Dashboard → Settings → API → JWT Secret
    
    # ==========================================================================
    # AI Agent Behavior
    # ==========================================================================
    ENABLE_AUTO_RESOLUTION: bool = True
    MAX_AUTO_ATTEMPTS: int = Field(default=3, ge=1, le=10)
    ESCALATION_CONFIDENCE_THRESHOLD: float = Field(default=0.7, ge=0.0, le=1.0)
    
    # ==========================================================================
    # Computed Properties
    # ==========================================================================
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.APP_ENV == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.APP_ENV == "production"


def get_settings() -> Settings:
    """
    Create and return a Settings instance.
    
    This function is used as a FastAPI dependency:
    
        @app.get("/")
        def root(settings: Settings = Depends(get_settings)):
            return {"app": settings.APP_NAME}
    
    We use a function (not a global variable) so settings can be
    overridden in tests.
    """
    return Settings()


# ---------------------------------------------------------------------------
# Module-level instance for convenience (non-test usage)
# ---------------------------------------------------------------------------
# This runs when the module is first imported. If .env is missing required
# fields, it crashes HERE with a clear error — not later in some random function.
settings = get_settings()
