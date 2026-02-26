from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation_message import ConversationMessage


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_message(
        self, scan_id: int, role: str, content: str, metadata: dict | None = None
    ) -> ConversationMessage:
        msg = ConversationMessage(
            scan_id=scan_id,
            role=role,
            content=content,
            metadata_=metadata or {},
        )
        self.db.add(msg)
        await self.db.flush()
        return msg

    async def get_history(self, scan_id: int) -> list[dict]:
        result = await self.db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.scan_id == scan_id)
            .order_by(ConversationMessage.created_at.asc())
        )
        messages = result.scalars().all()
        return [
            {"role": msg.role, "content": msg.content, "created_at": str(msg.created_at)}
            for msg in messages
        ]

    async def get_message_count(self, scan_id: int) -> int:
        result = await self.db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.scan_id == scan_id)
        )
        return len(result.scalars().all())
