from pydantic import BaseModel, Field, UUID4, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from .common import TimestampMixin


class VersionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    configuration: Dict[str, Any] = Field(default={})
    requested_tools: List[str] = Field(default=[])


class VersionCreate(VersionBase):
    created_by: str = Field(..., min_length=1)


class VersionActivate(BaseModel):
    activated_by: str = Field(..., min_length=1)


class VersionResponse(VersionBase, TimestampMixin):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    skill_id: UUID4
    version: int
    created_by: str
    is_active: bool
    activated_at: Optional[datetime] = None
    activated_by: Optional[str] = None


class VersionListResponse(BaseModel):
    versions: List[VersionResponse]
    total: int
