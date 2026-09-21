from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from .models import SubmissionStatus


class SubmissionResultResponse(BaseModel):
    requirement_id: int
    verdict: str
    evidence: str
    rationale: str
    evidence_verified: bool
    confidence: float

    model_config = {"from_attributes": True}


class SubmissionResponse(BaseModel):
    id: int
    user_id: str
    job_profile_id: int
    resume_filename: str
    status: SubmissionStatus
    overall_score: Optional[float]
    capped_by_must_have: Optional[bool]
    created_at: datetime
    results: list[SubmissionResultResponse]

    model_config = {"from_attributes": True}


class SubmissionListItem(BaseModel):
    id: int
    user_id: str
    job_profile_id: int
    resume_filename: str
    status: SubmissionStatus
    overall_score: Optional[float]
    capped_by_must_have: Optional[bool]
    created_at: datetime

    model_config = {"from_attributes": True}
