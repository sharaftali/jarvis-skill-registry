from pydantic import BaseModel, Field, UUID4, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum
from .common import TimestampMixin


class SkillStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DISABLED = "disabled"


class SkillBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)


class SkillCreate(SkillBase):
    owner_id: str = Field(..., min_length=1)
    requested_tools: List[str] = Field(default=[])


class SkillUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)


class SkillResponse(SkillBase, TimestampMixin):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    organization_id: str
    status: SkillStatus
    owner_id: str
    current_version_id: Optional[UUID4] = None


class SkillListResponse(BaseModel):
    skills: List[SkillResponse]
    total: int
