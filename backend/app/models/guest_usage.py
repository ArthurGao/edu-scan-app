from datetime import date, datetime

from sqlalchemy import BigInteger, Date, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class GuestUsage(Base):
    __tablename__ = "guest_usage"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ip_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    usage_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ip_hash", "usage_date", name="uq_guest_usage_ip_date"),
    )
