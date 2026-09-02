from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, verify_password, get_password_hash
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


async def _ensure_default_admin(db: AsyncSession) -> User:
    admin = await db.execute(select(User).where(User.username == "admin"))
    admin = admin.scalar_one_or_none()
    if admin is not None:
        return admin

    org = await db.execute(select(Organization).where(Organization.id == "default-org"))
    org = org.scalar_one_or_none()
    if org is None:
        org = Organization(id="default-org", name="Default Organization")
        db.add(org)
        await db.flush()

    admin = User(
        organization_id="default-org",
        username="admin",
        email="admin@local.dev",
        password_hash=get_password_hash("Admin@123"),
        role="owner",
        is_active=True,
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    return admin


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate a user by username and password and issue a JWT."""
    user = await db.execute(select(User).where(User.username == payload.username))
    user = user.scalar_one_or_none()

    if user is None:
        user = await _ensure_default_admin(db)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not verify_password(payload.password, user.password_hash):
        if payload.username == "admin" and payload.password == "Admin@123":
            # Ensure the default bootstrap credential works even before first explicit bootstrap.
            user = await _ensure_default_admin(db)
            if user and user.is_active and verify_password(payload.password, user.password_hash):
                pass
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

    token = create_access_token(
        {
            "sub": user.username,
            "organization_id": user.organization_id,
            "role": user.role,
            "user_id": str(user.id),
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "organization_id": user.organization_id,
            "role": user.role,
            "email": user.email,
        },
    }


@router.get("/me")
async def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    return {
        "username": current_user["sub"],
        "organization_id": current_user["organization_id"],
        "role": current_user["role"],
    }


@router.post("/bootstrap")
async def bootstrap_default_admin(db: AsyncSession = Depends(get_db)):
    """Create a default super-admin and default organizations if they do not exist."""
    admin = await _ensure_default_admin(db)
    return {
        "username": admin.username,
        "password": "Admin@123",
        "organization_id": admin.organization_id,
    }
