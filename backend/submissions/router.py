import asyncio
import logging
import uuid
from pathlib import Path

import anthropic
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.ai import compute_score, judge_requirement
from backend.ai.schemas import JobRequirement as AIJobRequirement, RequirementResult, Verdict
from backend.auth.dependencies import get_current_user, require_admin
from backend.auth.models import User
from backend.config import settings
from backend.database import get_db
from backend.limiter import limiter
from backend.parsing import parse_resume
from backend.profiles.models import JobProfile

from .models import Submission, SubmissionResult
from .schemas import SubmissionListItem, SubmissionResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/submissions", tags=["submissions"])

UPLOAD_DIR = Path(settings.upload_dir)

_ALLOWED_EXTENSIONS = {".pdf", ".docx"}
_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB
_MAX_RESUME_CHARS = 50_000           # ~12 500 tokens
_AI_TIMEOUT_SECONDS = 120.0

# Magic bytes: PDF = %PDF, DOCX = ZIP (PK\x03\x04)
_MAGIC = {
    ".pdf": b"%PDF",
    ".docx": b"PK\x03\x04",
}


def _ext(filename: str) -> str:
    return "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _check_magic(data: bytes, ext: str) -> bool:
    expected = _MAGIC.get(ext)
    return expected is not None and data[: len(expected)] == expected


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
@limiter.limit("10/hour")
async def submit_resume(
    request: Request,
    profile_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ext = _ext(file.filename or "")
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF and DOCX files are supported",
        )

    data = await file.read()

    if len(data) > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 10 MB limit",
        )

    if not _check_magic(data, ext):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File content does not match the declared file type",
        )

    try:
        resume_text = parse_resume(file.filename, data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not parse resume — ensure the file is a valid PDF or DOCX",
        )

    if len(resume_text) > _MAX_RESUME_CHARS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Resume exceeds maximum allowed length",
        )

    safe_filename = f"{uuid.uuid4()}{ext}"
    safe_path = UPLOAD_DIR / safe_filename
    safe_path.write_bytes(data)
    logger.info("Saved resume %s for user %s", safe_filename, current_user.id)

    try:
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

        try:
            raw = await asyncio.wait_for(
                asyncio.gather(
                    *[
                        loop.run_in_executor(None, judge_requirement, resume_text, ai_req, client)
                        for ai_req in ai_reqs
                    ],
                    return_exceptions=True,
                ),
                timeout=_AI_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="AI scoring timed out — please try again",
            )

        req_results: list[RequirementResult] = []
        for i, result in enumerate(raw):
            if isinstance(result, Exception):
                logger.error("Failed to judge requirement %s: %s", ai_reqs[i].id, result)
                req_results.append(
                    RequirementResult(
                        requirement_id=ai_reqs[i].id,
                        verdict=Verdict.not_met,
                        evidence="",
                        rationale="Evaluation failed — treated as not met",
                        evidence_verified=False,
                        confidence=0.0,
                    )
                )
            else:
                req_results.append(result)

        overall = compute_score(req_results, ai_reqs)

        submission = Submission(
            user_id=current_user.id,
            job_profile_id=profile_id,
            resume_filename=safe_filename,
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
        logger.info("Submission %s scored %.1f for user %s", submission.id, overall.score, current_user.id)

    finally:
        # File served its purpose (parsing + scoring); remove it to prevent disk accumulation
        safe_path.unlink(missing_ok=True)

    return await _load_submission(submission.id, db)


@router.get("/me", response_model=list[SubmissionListItem])
async def my_submissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Submission)
        .where(Submission.user_id == current_user.id)
        .order_by(Submission.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("", response_model=list[SubmissionListItem])
async def list_submissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(
        select(Submission)
        .order_by(Submission.overall_score.desc())
        .offset(skip)
        .limit(limit)
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile no longer exists")

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
