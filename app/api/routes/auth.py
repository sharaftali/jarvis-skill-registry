import asyncio
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, verify_password, get_password_hash
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
_startup_bootstrap_lock = asyncio.Lock()


async def _ensure_default_admin(db: AsyncSession) -> User:
    admin = await db.execute(select(User).where(User.username == settings.DEFAULT_ADMIN_USERNAME))
    admin = admin.scalar_one_or_none()
    if admin is not None:
        return admin

    org = await db.execute(select(Organization).where(Organization.id == settings.DEFAULT_ORGANIZATION_ID))
    org = org.scalar_one_or_none()
    if org is None:
        org = Organization(
            id=settings.DEFAULT_ORGANIZATION_ID,
            name=settings.DEFAULT_ORGANIZATION_NAME,
        )
        db.add(org)
        await db.flush()

    admin = User(
        organization_id=settings.DEFAULT_ORGANIZATION_ID,
        username=settings.DEFAULT_ADMIN_USERNAME,
        email=settings.DEFAULT_ADMIN_EMAIL,
        password_hash=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
        role="owner",
        is_active=True,
    )
    db.add(admin)
    await db.flush()
    await db.refresh(admin)
    return admin


async def initialize_default_admin() -> None:
    """Startup-only bootstrap for the default admin user and default-org tenant."""
    async with _startup_bootstrap_lock:
        bootstrap_engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            poolclass=NullPool,
        )
        async_session_factory = async_sessionmaker(
            bootstrap_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        try:
            async with async_session_factory() as db:
                try:
                    await _ensure_default_admin(db)
                    await db.commit()
                except Exception:
                    await db.rollback()
                    raise
        finally:
            await bootstrap_engine.dispose()


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate a user by username and password and issue a JWT."""
    user = await db.execute(select(User).where(User.username == payload.username))
    user = user.scalar_one_or_none()

    if user is None and payload.username == settings.DEFAULT_ADMIN_USERNAME:
        user = await _ensure_default_admin(db)
        await db.commit()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not verify_password(payload.password, user.password_hash):
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


@router.get("/me", dependencies=[Depends(get_current_user)])
async def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    return {
        "username": current_user["sub"],
        "organization_id": current_user["organization_id"],
        "role": current_user["role"],
    }


