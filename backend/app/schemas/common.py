from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    pages: int
    limit: int


class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
