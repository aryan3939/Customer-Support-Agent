"""
LLM factory — creates the right LLM client based on configuration.

WHY THIS FILE EXISTS:
---------------------
We support multiple LLM providers (Google AI Studio, Groq). Instead of
scattering provider-specific code everywhere, this file centralizes it:

    from src.agents.llm import get_llm
    llm = get_llm()  # Returns the right one based on .env settings

If you switch from Google to Groq, just change LLM_PROVIDER in .env.
No code changes needed!

HOW IT WORKS:
-------------
    .env: LLM_PROVIDER=google, GOOGLE_API_KEY=xxx
                    ↓
    get_llm() reads settings
                    ↓
    Returns ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.3)
"""

from langchain_core.language_models import BaseChatModel

from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


def get_llm() -> BaseChatModel:
    """
    Create and return an LLM client based on application settings.
    
    Returns:
        A LangChain chat model (Google Gemini or Groq).
        Both implement the same interface, so downstream code
        doesn't care which provider is used.
    
    Raises:
        ValueError: If LLM_PROVIDER is invalid or API key is missing.
    """
    
    if settings.LLM_PROVIDER == "google":
        # ---------------------------------------------------------------------
        # Google AI Studio (Gemini)
        # Free: 60 req/min, 1M tokens/day
        # ---------------------------------------------------------------------
        if not settings.GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY is required when LLM_PROVIDER=google. "
                "Get one at: https://aistudio.google.com/apikey"
            )
        
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        llm = ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
        )
        
        logger.info(
            "llm_initialized",
            provider="google",
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
        )
        return llm
    
    elif settings.LLM_PROVIDER == "groq":
        # ---------------------------------------------------------------------
        # Groq (Llama 3.1, Mixtral)
        # Free: 30 req/min, 14400 req/day
        # ---------------------------------------------------------------------
        if not settings.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is required when LLM_PROVIDER=groq. "
                "Get one at: https://console.groq.com/keys"
            )
        
        from langchain_groq import ChatGroq
        
        llm = ChatGroq(
            model=settings.LLM_MODEL,
            groq_api_key=settings.GROQ_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
        )
        
        logger.info(
            "llm_initialized",
            provider="groq",
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
        )
        return llm
    
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{settings.LLM_PROVIDER}'. "
            "Must be 'google' or 'groq'."
        )
