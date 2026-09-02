from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import OrganizationCreate, OrganizationResponse, OrgUserListResponse, UserCreate, UserResponse

router = APIRouter(prefix="/api/v1", tags=["organizations"])


@router.post("/organizations", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create an organization. Only authenticated owner users can create organizations."""
    if current_user.get("role") != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner users can create organizations",
        )

    org_id = payload.name.strip().lower().replace(" ", "-")
    existing = await db.execute(select(Organization).where(Organization.id == org_id))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization already exists",
        )

    org = Organization(id=org_id, name=payload.name.strip())
    db.add(org)
    await db.flush()

    if current_user.get("sub"):
        admin = await db.execute(select(User).where(User.username == current_user["sub"]))
        admin = admin.scalar_one_or_none()
        if admin is not None:
            admin.organization_id = org_id

    await db.commit()
    await db.refresh(org)
    return org


@router.post("/organizations/{organization_id}/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_org_user(
    organization_id: str,
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a user for an organization. Requires owner-level access."""
    if current_user.get("role") != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can create organization users",
        )

    is_bootstrap_admin = current_user.get("sub") == "admin"
    if not is_bootstrap_admin and current_user.get("organization_id") != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage users in your organization",
        )

    existing = await db.execute(select(User).where(User.username == payload.username))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    if payload.role not in {"owner", "member", "viewer"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be one of: owner, member, viewer",
        )

    user = User(
        organization_id=organization_id,
        username=payload.username,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/organizations/{organization_id}/users", response_model=OrgUserListResponse)
async def list_org_users(
    organization_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if current_user.get("role") not in {"owner", "member", "viewer"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    is_bootstrap_admin = current_user.get("sub") == "admin"
    if not is_bootstrap_admin and current_user.get("organization_id") != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only read users in your organization",
        )

    result = await db.execute(select(User).where(User.organization_id == organization_id))
    users = result.scalars().all()
    return {"users": users, "total": len(users)}
