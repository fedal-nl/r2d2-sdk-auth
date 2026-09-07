"""Validated authentication request and response models."""

from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, EmailStr, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Registration(StrictModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class Login(StrictModel):
    email: EmailStr
    password: str
    client_type: str = Field(default="python-sdk", max_length=30)


class Refresh(StrictModel):
    refresh_token: str = Field(min_length=32)


class TokenPair(StrictModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int = Field(gt=0)


class User(StrictModel):
    id: UUID
    username: str
    email: EmailStr | None
    avatar_url: AnyHttpUrl | None
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None
