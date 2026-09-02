from pydantic import BaseModel, ConfigDict, Field
from typing import List
from uuid import UUID


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    is_active: bool = True


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8)
    role: str = Field(default="member")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: str
    username: str
    email: str
    role: str
    is_active: bool


class OrgUserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
