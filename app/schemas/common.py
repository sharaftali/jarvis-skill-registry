from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel
from datetime import datetime

T = TypeVar('T')


class ResponseBase(BaseModel):
    success: bool = True
    message: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: Optional[datetime] = None
