from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.auth.dependencies import get_current_user, require_admin
from backend.auth.models import Role, User
from backend.database import get_db

from .models import JobProfile, Requirement
from .schemas import (
    CreateProfileRequest,
    ProfileListItem,
    ProfileResponse,
    RequirementPatch,
    RequirementResponse,
    UpdateProfileRequest,
)

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    body: CreateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    profile = JobProfile(
        title=body.title,
        keywords=body.keywords,
        created_by=current_user.id,
    )
    db.add(profile)
    await db.flush()

    for req in body.requirements:
        db.add(
            Requirement(
                job_profile_id=profile.id,
                text=req.text,
                weight=req.weight,
                must_have=req.must_have,
            )
        )

    await db.commit()

    result = await db.execute(
        select(JobProfile)
        .options(selectinload(JobProfile.requirements))
        .where(JobProfile.id == profile.id)
    )
    return result.scalar_one()


@router.get("", response_model=list[ProfileListItem])
async def list_profiles(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(JobProfile)
    if current_user.role != Role.ADMIN:
        stmt = stmt.where(JobProfile.is_active.is_(True))
    stmt = stmt.order_by(JobProfile.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(JobProfile)
        .options(selectinload(JobProfile.requirements))
        .where(JobProfile.id == profile_id)
    )
    if current_user.role != Role.ADMIN:
        stmt = stmt.where(JobProfile.is_active.is_(True))
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: int,
    body: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(
        select(JobProfile)
        .options(selectinload(JobProfile.requirements))
        .where(JobProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    if body.title is not None:
        profile.title = body.title
    if body.keywords is not None:
        profile.keywords = body.keywords
    if body.is_active is not None:
        profile.is_active = body.is_active

    await db.commit()
    await db.refresh(profile)
    return profile


@router.patch("/{profile_id}/requirements/{req_id}", response_model=RequirementResponse)
async def patch_requirement(
    profile_id: int,
    req_id: int,
    body: RequirementPatch,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(
        select(Requirement).where(
            Requirement.id == req_id,
            Requirement.job_profile_id == profile_id,
        )
    )
    req = result.scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")

    if body.weight is not None:
        req.weight = body.weight
    if body.must_have is not None:
        req.must_have = body.must_have

    await db.commit()
    await db.refresh(req)
    return req
