from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from uuid import UUID
from app.models.audit import AuditLog, AuditEventType
from app.schemas.audit import AuditLogResponse


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log_event(
        self,
        organization_id: str,
        actor: str,
        event_type: AuditEventType,
        skill_id: Optional[UUID] = None,
        version_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log an audit event"""
        audit_log = AuditLog(
            organization_id=organization_id,
            actor=actor,
            event_type=event_type,
            skill_id=skill_id,
            version_id=version_id,
            details=details or {},
        )
        self.db.add(audit_log)
        await self.db.flush()
        return audit_log
    
    async def get_audit_logs(
        self,
        organization_id: str,
        skill_id: Optional[UUID] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[AuditLog], int]:
        """Get audit logs with pagination."""
        query = select(AuditLog).where(AuditLog.organization_id == organization_id)
        count_query = select(func.count()).select_from(AuditLog).where(AuditLog.organization_id == organization_id)

        if skill_id:
            query = query.where(AuditLog.skill_id == skill_id)
            count_query = count_query.where(AuditLog.skill_id == skill_id)

        query = query.order_by(AuditLog.occurred_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)

        total = count_result.scalar() or 0
        return result.scalars().all(), int(total)
