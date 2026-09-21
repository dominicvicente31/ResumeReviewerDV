"""
ARQ worker — runs as a separate process and handles AI scoring jobs.

Start with:
    python -m arq backend.worker.WorkerSettings
"""

import asyncio
import logging

import anthropic
from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.ai import compute_score, judge_requirement
from backend.ai.schemas import JobRequirement as AIJobRequirement, RequirementResult, Verdict
from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.profiles.models import JobProfile
from backend.submissions.models import Submission, SubmissionResult, SubmissionStatus

logger = logging.getLogger(__name__)

_AI_TIMEOUT_SECONDS = 120.0


async def score_resume(ctx: dict, submission_id: int, resume_text: str) -> None:
    """
    ARQ task: run AI scoring for a submission.
    Called by the worker process after the API enqueues the job.
    Updates submission.status throughout so the client can poll.
    """
    async with AsyncSessionLocal() as db:
        sub = await db.get(Submission, submission_id)
        if sub is None:
            logger.error("score_resume called for missing submission %s", submission_id)
            return

        sub.status = SubmissionStatus.processing
        await db.commit()
        logger.info("Scoring submission %s", submission_id)

        try:
            profile_result = await db.execute(
                select(JobProfile)
                .options(selectinload(JobProfile.requirements))
                .where(JobProfile.id == sub.job_profile_id)
            )
            profile = profile_result.scalar_one_or_none()
            if profile is None:
                raise ValueError(f"Job profile {sub.job_profile_id} no longer exists")

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
            loop = asyncio.get_event_loop()

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
                raise ValueError("AI scoring timed out after 120 seconds")

            req_results: list[RequirementResult] = []
            for i, result in enumerate(raw):
                if isinstance(result, Exception):
                    logger.error("Requirement %s judgment failed: %s", ai_reqs[i].id, result)
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

            sub.overall_score = overall.score
            sub.capped_by_must_have = overall.capped_by_must_have
            sub.status = SubmissionStatus.completed

            for r in overall.per_requirement:
                db.add(
                    SubmissionResult(
                        submission_id=submission_id,
                        requirement_id=r.requirement_id,
                        verdict=r.verdict.value,
                        evidence=r.evidence,
                        rationale=r.rationale,
                        evidence_verified=r.evidence_verified,
                        confidence=r.confidence,
                    )
                )

            await db.commit()
            logger.info("Submission %s completed — score %.1f", submission_id, overall.score)

        except Exception as exc:
            logger.exception("Submission %s scoring failed: %s", submission_id, exc)
            sub.status = SubmissionStatus.failed
            await db.commit()
            raise


class WorkerSettings:
    functions = [score_resume]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 180
    keep_result = 300  # keep job result in Redis for 5 minutes
