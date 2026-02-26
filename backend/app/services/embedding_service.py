from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from app.llm.embeddings import embed_text
from app.models.scan_record import ScanRecord
from app.models.formula import Formula


class EmbeddingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def embed_scan_record(self, scan_id: int, text: str) -> None:
        """Generate and store embedding for a scan record."""
        try:
            vector = await embed_text(text)
            await self.db.execute(
                update(ScanRecord)
                .where(ScanRecord.id == scan_id)
                .values(embedding=vector)
            )
            await self.db.flush()
        except Exception:
            pass  # Non-critical: embedding failure shouldn't block solving

    async def embed_formula(self, formula_id: int, text: str) -> None:
        """Generate and store embedding for a formula."""
        try:
            vector = await embed_text(text)
            await self.db.execute(
                update(Formula)
                .where(Formula.id == formula_id)
                .values(embedding=vector)
            )
            await self.db.flush()
        except Exception:
            pass
