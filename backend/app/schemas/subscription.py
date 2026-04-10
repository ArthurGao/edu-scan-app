from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SubscriptionInfoResponse(BaseModel):
    tier_name: str
    display_name: str
    daily_limit: int
    used_today: int
    remaining_today: int
    features: Dict[str, Any]


class UsageHistoryResponse(BaseModel):
    date: date
    question_count: int


class AdminSetTierRequest(BaseModel):
    tier_name: str
