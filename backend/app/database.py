from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# Render/Neon provide postgresql:// URLs with params asyncpg doesn't understand.
# Strip incompatible query params and ensure the asyncpg driver is used.
_ASYNCPG_UNSUPPORTED_PARAMS = {"sslmode", "channel_binding", "options"}


def _fix_db_url(url: str) -> str:
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    # Convert sslmode → ssl for asyncpg
    if "sslmode" in params:
        ssl_val = params.pop("sslmode")[0]
        if ssl_val in ("require", "verify-ca", "verify-full"):
            params["ssl"] = ["require"]

    # Remove other unsupported params
    for key in _ASYNCPG_UNSUPPORTED_PARAMS:
        params.pop(key, None)

    clean_query = urlencode({k: v[0] for k, v in params.items()})
    return urlunparse(parsed._replace(query=clean_query))


_db_url = _fix_db_url(settings.database_url)

engine = create_async_engine(
    _db_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
