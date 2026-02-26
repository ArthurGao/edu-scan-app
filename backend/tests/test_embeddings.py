import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_embed_text_returns_vector():
    mock_vector = [0.1] * 1536
    with patch("app.llm.embeddings._embeddings") as mock_embeddings:
        mock_embeddings.aembed_query = AsyncMock(return_value=mock_vector)
        from app.llm.embeddings import embed_text
        result = await embed_text("solve 2x + 5 = 15")
        assert len(result) == 1536
        assert result == mock_vector
        mock_embeddings.aembed_query.assert_called_once_with("solve 2x + 5 = 15")


@pytest.mark.asyncio
async def test_embed_texts_batch():
    mock_vectors = [[0.1] * 1536, [0.2] * 1536]
    with patch("app.llm.embeddings._embeddings") as mock_embeddings:
        mock_embeddings.aembed_documents = AsyncMock(return_value=mock_vectors)
        from app.llm.embeddings import embed_texts
        result = await embed_texts(["text1", "text2"])
        assert len(result) == 2
        assert len(result[0]) == 1536
