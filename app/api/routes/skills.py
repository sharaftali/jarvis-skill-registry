from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_organization, get_owner_dependency
from app.schemas.skill import SkillCreate, SkillUpdate, SkillResponse, SkillListResponse
from app.schemas.version import VersionCreate, VersionResponse, VersionListResponse
from app.schemas.audit import AuditLogListResponse
from app.services.skill_service import SkillService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


@router.post("", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def create_skill(
    skill_data: SkillCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    organization_id: str = Depends(get_current_organization),
):
    """
    Create a new skill draft.
    
    Only authenticated users can create skills.
    The skill is created under the user's organization.
    """
    service = SkillService(db)
    
    # Use authenticated user's ID as the actor for audit logging
    actor = current_user["sub"]
    
    skill = await service.create_skill(
        organization_id=organization_id,
        skill_data=skill_data,
        actor=actor,
    )
    await db.commit()
    
    # Reload with relationships
    skill = await service.get_skill(organization_id, skill.id)
    return skill


@router.get("", response_model=SkillListResponse)
async def list_skills(
    status: Optional[str] = Query(None, pattern="^(draft|active|disabled)$"),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    organization_id: str = Depends(get_current_organization),
):
    """
    List skills for the current organization.
    
    Only skills belonging to the authenticated user's organization are returned.
    """
    service = SkillService(db)
    skills, total = await service.list_skills(
        organization_id=organization_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return SkillListResponse(skills=skills, total=total)


@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    organization_id: str = Depends(get_current_organization),
):
    """
    Get a skill by ID.
    
    Only skills belonging to the authenticated user's organization can be accessed.
    """
    service = SkillService(db)
    skill = await service.get_skill(organization_id, skill_id)
    return skill


@router.put("/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: UUID,
    skill_data: SkillUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    organization_id: str = Depends(get_current_organization),
):
    """
    Update skill metadata.
    
    Only authenticated users can update skills.
    The skill must belong to the user's organization.
    """
    service = SkillService(db)
    
    # Use authenticated user's ID as the actor for audit logging
    actor = current_user["sub"]
    
    skill = await service.update_skill(
        organization_id=organization_id,
        skill_id=skill_id,
        skill_data=skill_data,
        actor=actor,
    )
    await db.commit()
    
    # Reload
    skill = await service.get_skill(organization_id, skill_id)
    return skill


@router.post("/{skill_id}/versions", response_model=VersionResponse, status_code=status.HTTP_201_CREATED)
async def create_version(
    skill_id: UUID,
    version_data: VersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    organization_id: str = Depends(get_current_organization),
):
    """
    Create a new immutable version of a skill.
    
    Only authenticated users can create versions.
    The skill must belong to the user's organization.
    """
    service = SkillService(db)
    
    # Use authenticated user's ID as the actor
    actor = current_user["sub"]
    
    # Override created_by with authenticated user
    version_data.created_by = actor
    
    version = await service.create_version(
        organization_id=organization_id,
        skill_id=skill_id,
        version_data=version_data,
        actor=actor,
    )
    await db.commit()
    return version


@router.post("/{skill_id}/versions/{version_id}/activate", response_model=VersionResponse)
async def activate_version(
    skill_id: UUID,
    version_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    organization_id: str = Depends(get_current_organization),
    owner_org: str = Depends(get_owner_dependency),  # Ensures only owners can activate
):
    """
    Activate a version of a skill.
    
    ONLY ORGANIZATION OWNERS can activate a version.
    The skill must belong to the owner's organization.
    """
    service = SkillService(db)
    
    # Use authenticated user's ID as the actor
    actor = current_user["sub"]
    
    version = await service.activate_version(
        organization_id=organization_id,
        skill_id=skill_id,
        version_id=version_id,
        actor=actor,
    )
    await db.commit()
    return version


@router.post("/{skill_id}/disable", response_model=SkillResponse)
async def disable_skill(
    skill_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    organization_id: str = Depends(get_current_organization),
    owner_org: str = Depends(get_owner_dependency),  # Ensures only owners can disable
):
    """
    Disable a skill.
    
    ONLY ORGANIZATION OWNERS can disable a skill.
    The skill must belong to the owner's organization.
    """
    service = SkillService(db)
    
    # Use authenticated user's ID as the actor
    actor = current_user["sub"]
    
    skill = await service.disable_skill(
        organization_id=organization_id,
        skill_id=skill_id,
        actor=actor,
    )
    await db.commit()
    return skill


@router.get("/active/department/{department}", response_model=SkillListResponse)
async def get_active_skills_for_department(
    department: str,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    organization_id: str = Depends(get_current_organization),
):
    """
    Get active skills for a department.
    
    Only active skills from the authenticated user's organization are returned.
    """
    service = SkillService(db)
    skills, total = await service.get_active_skills_for_department(
        organization_id=organization_id,
        department=department,
        limit=limit,
        offset=offset,
    )
    return SkillListResponse(skills=skills, total=total)


@router.get("/{skill_id}/versions", response_model=VersionListResponse)
async def get_skill_versions(
    skill_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    organization_id: str = Depends(get_current_organization),
):
    """
    Get all versions of a skill.
    
    Only skills belonging to the authenticated user's organization can be accessed.
    """
    service = SkillService(db)
    _, versions = await service.get_skill_with_versions(
        organization_id=organization_id,
        skill_id=skill_id,
    )
    return VersionListResponse(versions=versions, total=len(versions))


@router.get("/{skill_id}/audit-logs", response_model=AuditLogListResponse)
async def get_skill_audit_logs(
    skill_id: UUID,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    organization_id: str = Depends(get_current_organization),
):
    """
    Get audit logs for a skill.
    
    Only audit logs from the authenticated user's organization can be accessed.
    """
    service = AuditService(db)
    logs, total = await service.get_audit_logs(
        organization_id=organization_id,
        skill_id=skill_id,
        limit=limit,
        offset=offset,
    )
    return AuditLogListResponse(logs=logs, total=total)
