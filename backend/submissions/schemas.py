from datetime import datetime

from pydantic import BaseModel


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
    overall_score: float
    capped_by_must_have: bool
    created_at: datetime
    results: list[SubmissionResultResponse]

    model_config = {"from_attributes": True}


class SubmissionListItem(BaseModel):
    id: int
    user_id: str
    job_profile_id: int
    resume_filename: str
    overall_score: float
    capped_by_must_have: bool
    created_at: datetime

    model_config = {"from_attributes": True}
