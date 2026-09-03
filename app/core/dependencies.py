from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .security import decode_token
from .config import settings
from app.core.database import get_db
from app.models.organization import Organization

security_scheme = HTTPBearer(
    scheme_name="bearerAuth",
    bearerFormat="JWT",
    auto_error=False,
)


async def _organization_is_valid(db: AsyncSession, organization_id: Optional[str]) -> bool:
    if not organization_id:
        return False
    if organization_id in settings.organization_list:
        return True
    result = await db.execute(select(Organization).where(Organization.id == organization_id))
    return result.scalar_one_or_none() is not None


async def get_current_user(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Authenticate the current user using a bearer JWT only."""
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is empty",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    required_claims = ["sub", "organization_id", "role"]
    missing_claims = [claim for claim in required_claims if claim not in payload]
    if missing_claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing required claims: {', '.join(missing_claims)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not await _organization_is_valid(db, payload["organization_id"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid organization in token: {payload['organization_id']}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload["role"] not in ["owner", "member", "viewer"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid role in token: {payload['role']}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def get_current_organization(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> str:
    """Return the authenticated user's organization. Never trust a request header or path for tenant scope."""
    return current_user["organization_id"]


async def get_owner_dependency(
    current_user: Dict[str, Any] = Depends(get_current_user),
    current_org: str = Depends(get_current_organization),
) -> str:
    """
    Verify the authenticated user has owner privileges.
    
    Only users with the role of 'owner' can perform owner-only operations
    such as activating a skill or disabling a skill.
    
    Returns the organization_id if the user is an owner.
    
    Raises 403 if the user is not an owner.
    """
    if current_user["role"] != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires owner privileges",
        )
    
    return current_org


# Alias for backward compatibility with existing code
# The canonical dependency is get_current_organization
get_organization = get_current_organization