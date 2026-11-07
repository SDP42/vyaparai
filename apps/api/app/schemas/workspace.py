import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.workspace import WorkspaceRole
from app.schemas.common import ORMModel


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")
    timezone: str = Field(default="Asia/Kolkata", max_length=64)

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    timezone: str | None = Field(default=None, max_length=64)


class WorkspaceRead(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    currency: str
    timezone: str
    created_at: datetime


class WorkspaceWithRole(WorkspaceRead):
    role: WorkspaceRole


class MemberAdd(BaseModel):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.VIEWER

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, v: str) -> str:
        return v.strip().lower()


class MemberRead(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    role: WorkspaceRole
    joined_at: datetime
