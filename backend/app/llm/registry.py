from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel

from app.config import get_settings

LLM_REGISTRY: dict[str, type[BaseChatModel]] = {
    "claude": ChatAnthropic,
    "openai": ChatOpenAI,
    "gemini": ChatGoogleGenerativeAI,
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
) -> BaseChatModel:
    """Select LLM based on preference, subject, and retry rotation."""
    providers = list(LLM_REGISTRY.keys())

    if attempt == 0:
        provider = preferred or SUBJECT_PROVIDER_MAP.get(subject, "claude")
    else:
        base = preferred or SUBJECT_PROVIDER_MAP.get(subject, "claude")
        idx = providers.index(base) if base in providers else 0
        provider = providers[(idx + attempt) % len(providers)]

    return get_llm("strong", provider)
