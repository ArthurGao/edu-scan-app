from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.language_models import BaseChatModel

from app.config import get_settings

LLM_REGISTRY: dict[str, type[BaseChatModel]] = {
    "claude": ChatAnthropic,
    "openai": ChatOpenAI,
    "gemini": ChatGoogleGenerativeAI,
    "groq": ChatGroq,
}

MODEL_CONFIG: dict[str, dict[str, str]] = {
    "claude": {
        "strong": "claude-sonnet-4-20250514",
        "fast": "claude-haiku-4-5-20251001",
    },
    "openai": {
        "strong": "gpt-4o",
        "fast": "gpt-4o-mini",
    },
    "gemini": {
        "strong": "gemini-2.5-flash",
        "fast": "gemini-2.5-flash-lite",
        "verify": "gemini-2.5-flash-lite",
        "evaluate": "gemini-2.5-flash",
        "grading": "gemini-2.5-flash",
    },
    "groq": {
        "strong": "qwen-qwq-32b",
        "fast": "qwen3-32b",
    },
}

SUBJECT_PROVIDER_MAP: dict[str, str] = {
    "math": "claude",
    "physics": "claude",
    "chemistry": "openai",
    "biology": "openai",
    "english": "openai",
    "chinese": "claude",
}


def _get_api_key_kwargs(provider: str) -> dict:
    """Return the API key kwargs for the given provider."""
    settings = get_settings()
    if provider == "claude":
        key = settings.anthropic_api_key
        return {"api_key": key} if key else {}
    elif provider == "openai":
        key = settings.openai_api_key
        return {"api_key": key} if key else {}
    elif provider == "gemini":
        key = settings.google_api_key
        return {"google_api_key": key} if key else {}
    elif provider == "groq":
        key = settings.groq_api_key
        return {"api_key": key} if key else {}
    return {}


def get_llm(tier: str = "strong", provider: str | None = None) -> BaseChatModel:
    """Get a ChatModel instance by tier and provider."""
    settings = get_settings()
    provider = provider or settings.default_ai_provider
    if provider not in LLM_REGISTRY:
        raise ValueError(f"Unknown provider: {provider}. Available: {list(LLM_REGISTRY.keys())}")
    if tier not in MODEL_CONFIG.get(provider, {}):
        available = list(MODEL_CONFIG.get(provider, {}).keys())
        raise ValueError(f"Unknown tier: {tier}. Available: {available}")

    cls = LLM_REGISTRY[provider]
    model = MODEL_CONFIG[provider][tier]
    kwargs = _get_api_key_kwargs(provider)
    return cls(model=model, temperature=0.1, **kwargs)


def select_llm(
    preferred: str | None,
    subject: str,
    attempt: int = 0,
    user_tier: str = "paid",
) -> BaseChatModel:
    """Select LLM based on preference, subject, retry rotation, and user tier.

    For paid users: subject-based routing (Claude/OpenAI).
    For free users: Gemini → Groq fallback chain.
    """
    if user_tier == "free":
        # Free tier: Gemini first, then Groq fallback
        free_chain = [
            ("gemini", "strong"),
            ("groq", "strong"),
            ("groq", "fast"),
        ]
        idx = min(attempt, len(free_chain) - 1)
        provider, tier = free_chain[idx]
        return get_llm(tier, provider)

    # Paid tier: existing subject-based routing
    providers = list(LLM_REGISTRY.keys())

    if attempt == 0:
        provider = preferred or SUBJECT_PROVIDER_MAP.get(subject, "claude")
    else:
        base = preferred or SUBJECT_PROVIDER_MAP.get(subject, "claude")
        idx = providers.index(base) if base in providers else 0
        provider = providers[(idx + attempt) % len(providers)]

    return get_llm("strong", provider)
