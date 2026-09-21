import asyncio

import anthropic
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.ai import compute_score, judge_requirement
from backend.ai.schemas import JobRequirement as AIJobRequirement, RequirementResult, Verdict
from backend.auth.dependencies import get_current_user, require_admin
from backend.auth.models import User
from backend.database import get_db
from backend.parsing import parse_resume
from backend.profiles.models import JobProfile

from .models import Submission, SubmissionResult
from .schemas import SubmissionListItem, SubmissionResponse

router = APIRouter(prefix="/submissions", tags=["submissions"])

_ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def _ext(filename: str) -> str:
    return "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


async def _load_submission(submission_id: int, db: AsyncSession) -> Submission:
    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.results))
        .where(Submission.id == submission_id)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    return sub


@router.post("", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_resume(
    profile_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if _ext(file.filename) not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF and DOCX files are supported",
        )

    data = await file.read()
    try:
        resume_text = parse_resume(file.filename, data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse resume: {exc}",
        )

    profile_result = await db.execute(
        select(JobProfile)
        .options(selectinload(JobProfile.requirements))
        .where(JobProfile.id == profile_id, JobProfile.is_active.is_(True))
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job profile not found")
    if not profile.requirements:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Job profile has no requirements",
        )

    ai_reqs = [
        AIJobRequirement(
            id=req.id,
            text=req.text,
            weight=req.weight,
            must_have=req.must_have,
        )
        for req in profile.requirements
    ]

    client = anthropic.Anthropic()
    loop = asyncio.get_running_loop()
    req_results: list[RequirementResult] = list(
        await asyncio.gather(*[
            loop.run_in_executor(None, judge_requirement, resume_text, ai_req, client)
            for ai_req in ai_reqs
        ])
    )

    overall = compute_score(req_results, ai_reqs)

    submission = Submission(
        user_id=current_user.id,
        job_profile_id=profile_id,
        resume_filename=file.filename,
        overall_score=overall.score,
        capped_by_must_have=overall.capped_by_must_have,
    )
    db.add(submission)
    await db.flush()

    for r in overall.per_requirement:
        db.add(
            SubmissionResult(
                submission_id=submission.id,
                requirement_id=r.requirement_id,
                verdict=r.verdict.value,
                evidence=r.evidence,
                rationale=r.rationale,
                evidence_verified=r.evidence_verified,
                confidence=r.confidence,
            )
        )

    await db.commit()
    return await _load_submission(submission.id, db)


@router.get("/me", response_model=list[SubmissionListItem])
async def my_submissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Submission)
        .where(Submission.user_id == current_user.id)
        .order_by(Submission.created_at.desc())
    )
    return result.scalars().all()


@router.get("", response_model=list[SubmissionListItem])
async def list_submissions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(
        select(Submission).order_by(Submission.overall_score.desc())
    )
    return result.scalars().all()


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from backend.auth.models import Role

    sub = await _load_submission(submission_id, db)
    if current_user.role != Role.ADMIN and sub.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return sub


@router.post("/{submission_id}/rescore", response_model=SubmissionResponse)
async def rescore_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    sub = await _load_submission(submission_id, db)

    profile_result = await db.execute(
        select(JobProfile)
        .options(selectinload(JobProfile.requirements))
        .where(JobProfile.id == sub.job_profile_id)
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile no longer exists"
        )

    req_map = {req.id: req for req in profile.requirements}
    ai_reqs = [
        AIJobRequirement(id=req.id, text=req.text, weight=req.weight, must_have=req.must_have)
        for req in profile.requirements
    ]
    ai_results = [
        RequirementResult(
            requirement_id=r.requirement_id,
            verdict=Verdict(r.verdict),
            evidence=r.evidence,
            rationale=r.rationale,
            evidence_verified=r.evidence_verified,
            confidence=r.confidence,
        )
        for r in sub.results
        if r.requirement_id in req_map
    ]

    overall = compute_score(ai_results, ai_reqs)
    sub.overall_score = overall.score
    sub.capped_by_must_have = overall.capped_by_must_have

    await db.commit()
    return await _load_submission(submission_id, db)
