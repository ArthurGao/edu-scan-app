import logging
import httpx
from langchain_openai import OpenAIEmbeddings
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_GOOGLE_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-embedding-001:embedContent"
)

_openai_embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    dimensions=768,
    api_key=settings.openai_api_key or "dummy",
)


async def _google_embed(text: str) -> list[float]:
    """Call Google Generative Language v1 REST API directly."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            _GOOGLE_EMBED_URL,
            params={"key": settings.google_api_key},
            json={"model": "models/gemini-embedding-001", "content": {"parts": [{"text": text}]}, "outputDimensionality": 768},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]["values"]


async def _google_embed_batch(texts: list[str]) -> list[list[float]]:
    import asyncio
    return await asyncio.gather(*[_google_embed(t) for t in texts])


async def embed_text(text: str) -> list[float]:
    """Generate embedding vector. Google default, OpenAI fallback."""
    try:
        return await _google_embed(text)
    except Exception as e:
        logger.warning("Google embedding failed, falling back to OpenAI: %s", e)
        return await _openai_embeddings.aembed_query(text)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embedding vectors for multiple texts. Google default, OpenAI fallback."""
    try:
        return await _google_embed_batch(texts)
    except Exception as e:
        logger.warning("Google embedding failed, falling back to OpenAI: %s", e)
        return await _openai_embeddings.aembed_documents(texts)
