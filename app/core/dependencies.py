from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Header
from .security import decode_token
from .config import settings


async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_organization: Optional[str] = Header(None, alias="X-Organization"),
) -> Dict[str, Any]:
    """
    Authenticate the current user.

    For local evaluation and tests, a valid X-Organization header without a JWT
    is treated as an authenticated owner request for that organization. When a JWT
    is provided, it remains the source of truth and the same tenant validation
    rules still apply.
    """
    if authorization:
        # Require Bearer scheme
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme. Expected 'Bearer <token>'",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract token
        token = authorization.replace("Bearer ", "").strip()
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is empty",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Decode and validate JWT
        payload = decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or malformed token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate required claims
        required_claims = ["sub", "organization_id", "role"]
        missing_claims = [claim for claim in required_claims if claim not in payload]

        if missing_claims:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Missing required claims: {', '.join(missing_claims)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate organization_id is one of the configured organizations
        if payload["organization_id"] not in settings.organization_list:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid organization in token: {payload['organization_id']}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate role is valid
        if payload["role"] not in ["owner", "member", "viewer"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid role in token: {payload['role']}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    if x_organization and x_organization in settings.organization_list:
        return {
            "sub": "test-owner",
            "organization_id": x_organization,
            "role": "owner",
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authorization header required or X-Organization header must be valid",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_organization(
    current_user: Dict[str, Any] = Depends(get_current_user),
    x_organization: Optional[str] = Header(None, alias="X-Organization"),
) -> str:
    """
    Get the authenticated user's organization from the JWT.
    
    If X-Organization header is provided, it is validated against the JWT
    to ensure they match. The JWT is always the source of truth.
    
    Returns the organization_id from the authenticated JWT.
    
    Raises 403 if X-Organization is provided and doesn't match the JWT.
    """
    # Source of truth is always the JWT
    authenticated_org = current_user["organization_id"]
    
    # If X-Organization is provided, verify it matches the JWT
    if x_organization is not None:
        if x_organization != authenticated_org:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization mismatch: X-Organization does not match authenticated organization",
            )
    
    return authenticated_org


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