from pydantic import BaseModel, UUID4, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class AuditEventType(str, Enum):
    SKILL_CREATED = "skill_created"
    SKILL_UPDATED = "skill_updated"
    SKILL_ACTIVATED = "skill_activated"
    SKILL_DISABLED = "skill_disabled"
    VERSION_CREATED = "version_created"
    VERSION_ACTIVATED = "version_activated"


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    organization_id: str
    skill_id: Optional[UUID4] = None
    version_id: Optional[UUID4] = None
    event_type: AuditEventType
    actor: str
    details: Dict[str, Any]
    occurred_at: datetime


class AuditLogListResponse(BaseModel):
    logs: List[AuditLogResponse]
    total: int
