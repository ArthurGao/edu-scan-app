import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import from_url as redis_from_url
from sqlalchemy import text

from app.api.v1.router import api_router
from app.config import get_settings
from app.core.rate_limiter import RateLimitMiddleware
from app.database import engine

logger = logging.getLogger(__name__)
settings = get_settings()

# Silence SQLAlchemy SQL echo regardless of debug mode
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

_redis = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis
    # Startup — fix sequences that may be out of sync with seeded data
    async with engine.begin() as conn:
        await conn.execute(text(
            "SELECT setval('formulas_id_seq', COALESCE((SELECT MAX(id) FROM formulas), 0))"
        ))
    # Initialize Redis for rate limiting
    if settings.rate_limit_enabled:
        try:
            _redis = redis_from_url(settings.redis_url, decode_responses=True)
            await _redis.ping()
            logger.info("Rate limiter connected to Redis")
        except Exception as e:
            logger.warning("Rate limiter Redis unavailable, rate limiting disabled: %s", e)
            _redis = None
    yield
    # Shutdown
    if _redis:
        await _redis.aclose()


app = FastAPI(
    title=settings.app_name,
    description="AI-powered educational problem solver",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# CORS Middleware (outermost — runs first on response)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting Middleware
if settings.rate_limit_enabled:
    # Use a lazy Redis reference; the actual connection is established in lifespan.
    # RateLimitMiddleware.dispatch checks redis availability and fails open.
    _lazy_redis = redis_from_url(settings.redis_url, decode_responses=True)
    app.add_middleware(RateLimitMiddleware, redis=_lazy_redis)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.app_name}
