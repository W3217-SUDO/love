"""Pydantic schemas for auth API requests and responses."""
from pydantic import BaseModel, Field


class BindInfo(BaseModel):
    """GET /bind response — shown to the user before they pick a password."""
    token: str
    username: str
    display_name: str
    role: str


class BindRequest(BaseModel):
    """POST /bind body."""
    token: str = Field(min_length=1)
    password: str = Field(min_length=8, max_length=256)


class UserPublic(BaseModel):
    """Subset of User fields safe to return to the API caller."""
    id: int
    username: str
    display_name: str
    role: str


class BindResponse(BaseModel):
    status: str
    user: UserPublic


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    status: str
    user: UserPublic
