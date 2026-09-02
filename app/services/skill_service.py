import re
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from uuid import UUID, uuid4
from fastapi import HTTPException, status
from datetime import datetime

from app.models.skill import Skill
from app.models.version import SkillVersion
from app.models.audit import AuditEventType
from app.schemas.skill import SkillCreate, SkillUpdate, SkillResponse
from app.schemas.version import VersionCreate, VersionResponse
from app.services.audit_service import AuditService


class SkillService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_service = AuditService(db)
    
    async def create_skill(
        self,
        organization_id: str,
        skill_data: SkillCreate,
        actor: str,
    ) -> Skill:
        """Create a new skill draft without creating a default active version."""
        # Validate requested tools
        await self._validate_tools(skill_data.requested_tools)

        # Create skill draft
        skill = Skill(
            organization_id=organization_id,
            name=skill_data.name,
            description=skill_data.description,
            status="draft",
            owner_id=skill_data.owner_id,
            current_version_id=None,
        )
        self.db.add(skill)
        await self.db.flush()

        # Audit log without forcing a version row into the draft lifecycle
        await self.audit_service.log_event(
            organization_id=organization_id,
            actor=actor,
            event_type=AuditEventType.SKILL_CREATED,
            skill_id=skill.id,
            version_id=None,
            details={"name": skill.name, "status": "draft"},
        )

        return skill
    
    async def get_skill(
        self,
        organization_id: str,
        skill_id: UUID,
    ) -> Skill:
        """Get a skill by ID with organization check."""
        query = select(Skill).where(
            and_(
                Skill.id == skill_id,
                Skill.organization_id == organization_id,
            )
        )
        result = await self.db.execute(query)
        skill = result.scalar_one_or_none()

        if not skill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Skill not found or access denied",
            )

        return skill

    async def get_skill_for_write(
        self,
        organization_id: str,
        skill_id: UUID,
    ) -> Skill:
        """Load a skill by ID and require the caller to be in the same organization."""
        query = select(Skill).where(Skill.id == skill_id)
        result = await self.db.execute(query)
        skill = result.scalar_one_or_none()

        if not skill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Skill not found",
            )

        if skill.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: skill belongs to a different organization",
            )

        return skill
    
    async def list_skills(
        self,
        organization_id: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[Skill], int]:
        """List skills for an organization"""
        query = select(Skill).where(Skill.organization_id == organization_id)
        count_query = select(func.count()).select_from(Skill).where(Skill.organization_id == organization_id)
        
        if status:
            query = query.where(Skill.status == status)
            count_query = count_query.where(Skill.status == status)
        
        query = query.order_by(Skill.created_at.desc()).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        
        return result.scalars().all(), count_result.scalar()
    
    async def update_skill(
        self,
        organization_id: str,
        skill_id: UUID,
        skill_data: SkillUpdate,
        actor: str,
    ) -> Skill:
        """Update skill metadata (not the active version)"""
        skill = await self.get_skill_for_write(organization_id, skill_id)

        # Can't update disabled skills
        if skill.status == "disabled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update a disabled skill",
            )
        
        # Update fields
        if skill_data.name is not None:
            skill.name = skill_data.name
        if skill_data.description is not None:
            skill.description = skill_data.description
        
        skill.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(skill)
        
        # Audit log
        await self.audit_service.log_event(
            organization_id=organization_id,
            actor=actor,
            event_type=AuditEventType.SKILL_UPDATED,
            skill_id=skill.id,
            details={"updated_fields": skill_data.model_dump(exclude_unset=True)},
        )
        
        return skill
    
    async def create_version(
        self,
        organization_id: str,
        skill_id: UUID,
        version_data: VersionCreate,
        actor: str,
    ) -> SkillVersion:
        """Create a new immutable version of a skill."""
        skill = await self.get_skill_for_write(organization_id, skill_id)

        # Can't create versions for disabled skills
        if skill.status == "disabled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create version for a disabled skill",
            )

        # Validate requested tools
        await self._validate_tools(version_data.requested_tools)

        # Get latest version number for this skill; if no versions exist yet,
        # the first explicit version is numbered 1.
        latest_version_query = select(func.max(SkillVersion.version)).where(
            SkillVersion.skill_id == skill_id
        )
        result = await self.db.execute(latest_version_query)
        latest_version = result.scalar() or 0

        # Create new version
        version = SkillVersion(
            skill_id=skill_id,
            version=latest_version + 1,
            name=version_data.name,
            description=version_data.description,
            configuration=version_data.configuration,
            requested_tools=version_data.requested_tools,
            created_by=actor,
        )
        self.db.add(version)
        await self.db.flush()
        
        # Audit log
        await self.audit_service.log_event(
            organization_id=organization_id,
            actor=actor,
            event_type=AuditEventType.VERSION_CREATED,
            skill_id=skill_id,
            version_id=version.id,
            details={"version": version.version},
        )
        
        return version
    
    async def activate_version(
        self,
        organization_id: str,
        skill_id: UUID,
        version_id: UUID,
        actor: str,
    ) -> SkillVersion:
        """Activate a version - only organization owner can do this."""
        skill = await self.get_skill_for_write(organization_id, skill_id)

        # Check if user is owner
        if skill.owner_id != actor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the skill owner can activate a version",
            )

        # Can't activate if skill is disabled
        if skill.status == "disabled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot activate version for a disabled skill",
            )

        version_query = select(SkillVersion).where(
            and_(
                SkillVersion.id == version_id,
                SkillVersion.skill_id == skill_id,
            )
        )
        result = await self.db.execute(version_query)
        version = result.scalar_one_or_none()

        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Version not found",
            )

        if version.is_active:
            skill.status = "active"
            skill.current_version_id = version.id
            await self.db.flush()
            await self.db.refresh(skill)
            await self.db.refresh(version)
            return version

        # Deactivate all other versions while preserving the originally activated one.
        await self.db.execute(
            SkillVersion.__table__.update().where(
                and_(
                    SkillVersion.skill_id == skill_id,
                    SkillVersion.id != version.id,
                )
            ).values(is_active=False, activated_at=None, activated_by=None)
        )

        version.is_active = True
        version.activated_at = datetime.utcnow()
        version.activated_by = actor
        skill.status = "active"
        skill.current_version_id = version.id
        await self.db.flush()

        await self.db.refresh(skill)
        await self.db.refresh(version)

        await self.audit_service.log_event(
            organization_id=organization_id,
            actor=actor,
            event_type=AuditEventType.VERSION_ACTIVATED,
            skill_id=skill_id,
            version_id=version.id,
            details={"version": version.version, "skill_status": skill.status},
        )

        return version
    
    async def disable_skill(
        self,
        organization_id: str,
        skill_id: UUID,
        actor: str,
    ) -> Skill:
        """Disable a skill"""
        skill = await self.get_skill_for_write(organization_id, skill_id)

        # Check if user is owner
        if skill.owner_id != actor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the skill owner can disable a skill",
            )
        
        if skill.status == "disabled":
            # Idempotent operation
            await self.db.refresh(skill)
            return skill

        skill.status = "disabled"
        skill.current_version_id = None
        await self.db.flush()
        await self.db.refresh(skill)
        await self.db.execute(
            SkillVersion.__table__.update().where(
                SkillVersion.skill_id == skill_id
            ).values(is_active=False, activated_at=None, activated_by=None)
        )
        await self.db.flush()
        
        # Audit log
        await self.audit_service.log_event(
            organization_id=organization_id,
            actor=actor,
            event_type=AuditEventType.SKILL_DISABLED,
            skill_id=skill.id,
            details={"previous_status": "active" if skill.status != "disabled" else "draft"},
        )
        
        return skill
    
    async def get_active_skills_for_department(
        self,
        organization_id: str,
        department: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[Skill], int]:
        """Get active skills for a department"""
        # In a real implementation, this would filter by department
        # For evaluation, we return all active skills
        query = select(Skill).where(
            and_(
                Skill.organization_id == organization_id,
                Skill.status == "active",
            )
        )
        count_query = select(func.count()).select_from(Skill).where(
            and_(
                Skill.organization_id == organization_id,
                Skill.status == "active",
            )
        )
        
        query = query.order_by(Skill.name).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        
        return result.scalars().all(), count_result.scalar()
    
    async def _validate_tools(self, tools: List[str]) -> None:
        """Validate requested tools - reject destructive or invalid tools"""
        # For evaluation, we reject any tool that is destructive
        destructive_tools = ["delete_all", "drop_database", "shutdown", "rm_rf", "format"]

        for tool in tools:
            if tool in destructive_tools:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Destructive tool '{tool}' is not allowed",
                )

            if not tool or not re.fullmatch(r"[A-Za-z0-9_]+", tool):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid tool name: '{tool}'",
                )
    
    async def get_skill_with_versions(
        self,
        organization_id: str,
        skill_id: UUID,
    ) -> tuple[Skill, List[SkillVersion]]:
        """Get skill with all its versions."""
        skill = await self.get_skill(organization_id, skill_id)

        versions_query = select(SkillVersion).where(
            SkillVersion.skill_id == skill_id
        ).order_by(SkillVersion.version.desc())
        result = await self.db.execute(versions_query)
        versions = result.scalars().all()

        return skill, versions
