from datetime import datetime

from pydantic import BaseModel, Field


class RequirementIn(BaseModel):
    text: str
    weight: float = Field(ge=0.0, le=1.0)
    must_have: bool = False


class RequirementResponse(BaseModel):
    id: int
    text: str
    weight: float
    must_have: bool

    model_config = {"from_attributes": True}


class RequirementPatch(BaseModel):
    weight: float | None = Field(default=None, ge=0.0, le=1.0)
    must_have: bool | None = None


class CreateProfileRequest(BaseModel):
    title: str
    keywords: list[str] = []
    requirements: list[RequirementIn]


class UpdateProfileRequest(BaseModel):
    title: str | None = None
    keywords: list[str] | None = None
    is_active: bool | None = None


class ProfileListItem(BaseModel):
    id: int
    title: str
    keywords: list[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProfileResponse(BaseModel):
    id: int
    title: str
    keywords: list[str]
    is_active: bool
    created_by: str
    created_at: datetime
    requirements: list[RequirementResponse]

    model_config = {"from_attributes": True}
