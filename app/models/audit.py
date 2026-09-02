from app.schemas.audit import AuditEventType
from sqlalchemy import Column, DateTime, String, JSON, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base




class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(String, nullable=False, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=True)
    version_id = Column(UUID(as_uuid=True), ForeignKey("skill_versions.id", ondelete="CASCADE"), nullable=True)
    event_type = Column(Enum(AuditEventType), nullable=False)
    actor = Column(String, nullable=False)
    details = Column(JSON, default={})
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    skill = relationship("Skill", back_populates="audit_logs")
    version = relationship("SkillVersion", back_populates="audit_logs")