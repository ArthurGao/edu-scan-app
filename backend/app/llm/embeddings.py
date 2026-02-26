from langchain_openai import OpenAIEmbeddings
from app.config import get_settings

settings = get_settings()

_embeddings = OpenAIEmbeddings(
    model=settings.embedding_model,
    api_key=settings.openai_api_key or "dummy",
)


async def embed_text(text: str) -> list[float]:
    """Generate embedding vector for a single text."""
    return await _embeddings.aembed_query(text)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embedding vectors for multiple texts."""
    return await _embeddings.aembed_documents(texts)
