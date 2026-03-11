"""Cache check node — runs after OCR, before analyze/solve.

Layer 1: Redis exact match (SHA256 of ocr_text) → return cached response, skip to END
Layer 2: pgvector cosine similarity > 0.95   → return cached response, skip to END
Layer 3: pgvector cosine similarity 0.80-0.95 → inject framework, use Haiku in solve_node
Layer 4: no cache match                       → full Sonnet solve (normal flow)
"""
import hashlib
import json
import logging

from redis.asyncio import from_url as redis_from_url

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.graph.state import SolveState

logger = logging.getLogger(__name__)

LAYER2_THRESHOLD = 0.95
LAYER3_THRESHOLD = 0.80

_settings = get_settings()
_redis = redis_from_url(_settings.redis_url, decode_responses=True)


def _make_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


async def check_cache_node(state: SolveState) -> dict:
    """Check all cache layers and short-circuit if a usable result is found."""
    ocr_text = state.get("ocr_text", "").strip()
    if not ocr_text:
        return {"cache_hit": False, "cache_layer": 4}

    cache_key = _make_key(ocr_text)

    # ── Layer 1: Redis exact match ──────────────────────────────────────────
    try:
        cached_json = await _redis.get(f"solve:{cache_key}")
        if cached_json:
            cached = json.loads(cached_json)
            logger.info("Cache Layer 1 hit (exact, Redis)")
            return {
                "cache_hit": True,
                "cache_layer": 1,
                "solution_parsed": cached,
                "solution_raw": cached_json,
                "final_solution": cached,
                "llm_provider": "cache",
                "llm_model": "layer1",
                "prompt_tokens": 0,
                "completion_tokens": 0,
            }
    except Exception as e:
        logger.warning("Redis Layer 1 check failed: %s", e)

    # ── Layer 2 & 3: pgvector semantic similarity ───────────────────────────
    try:
        from pgvector.sqlalchemy import Vector  # noqa: F401 — ensures extension available
        from sqlalchemy import func, select, update

        from app.llm.embeddings import embed_text
        from app.models.semantic_cache import SemanticCache

        embedding = await embed_text(ocr_text)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(
                    SemanticCache,
                    (1 - SemanticCache.embedding.cosine_distance(embedding)).label("similarity"),
                )
                .where(SemanticCache.embedding.isnot(None))
                .order_by(SemanticCache.embedding.cosine_distance(embedding))
                .limit(1)
            )
            row = result.first()

            if row:
                entry, similarity = row
                logger.info("Semantic similarity: %.4f", similarity)

                # Bump hit count (fire-and-forget)
                await db.execute(
                    update(SemanticCache)
                    .where(SemanticCache.id == entry.id)
                    .values(hit_count=SemanticCache.hit_count + 1, last_hit_at=func.now())
                )
                await db.commit()

                if similarity >= LAYER2_THRESHOLD:
                    logger.info("Cache Layer 2 hit (semantic, sim=%.4f)", similarity)
                    cached_response = entry.response
                    return {
                        "cache_hit": True,
                        "cache_layer": 2,
                        "solution_parsed": cached_response,
                        "solution_raw": json.dumps(cached_response),
                        "final_solution": cached_response,
                        "llm_provider": "cache",
                        "llm_model": "layer2",
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                    }

                if similarity >= LAYER3_THRESHOLD:
                    logger.info("Cache Layer 3 (framework reuse, sim=%.4f)", similarity)
                    return {
                        "cache_hit": False,
                        "cache_layer": 3,
                        "solution_framework": entry.solution_framework,
                    }

    except Exception as e:
        logger.warning("Semantic cache check failed: %s", e)

    logger.info("Cache MISS — proceeding to full solve (Layer 4)")
    return {"cache_hit": False, "cache_layer": 4}
