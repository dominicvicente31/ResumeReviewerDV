from enum import Enum
from pydantic import BaseModel, Field


class Verdict(str, Enum):
    MET = "met"
    PARTIAL = "partial"
    NOT_MET = "not_met"


class LLMJudgment(BaseModel):
    """Structured output schema for a single LLM judgment call."""
    verdict: Verdict = Field(description="met, partial, or not_met")
    evidence: str = Field(
        description="Short direct quote from the resume supporting the verdict, or empty string"
    )
    rationale: str = Field(description="One sentence explaining the verdict")


class JobRequirement(BaseModel):
    id: int
    text: str
    weight: float = Field(ge=0.0, le=1.0, description="Relative importance")
    must_have: bool = False


class RequirementResult(BaseModel):
    """Per-requirement output with confidence signals derived from code, not the model."""
    requirement_id: int
    verdict: Verdict
    evidence: str
    rationale: str
    evidence_verified: bool  # quote actually found in resume text
    confidence: float = Field(ge=0.0, le=1.0)


class OverallResult(BaseModel):
    score: float = Field(ge=0.0, le=100.0)
    capped_by_must_have: bool
    per_requirement: list[RequirementResult]
