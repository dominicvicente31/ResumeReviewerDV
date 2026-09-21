"""
AI layer for ResumeReviewerDV.

Typical usage
-------------
    import anthropic
    from backend.ai import judge_requirement, compute_score, JobRequirement

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    requirements = [
        JobRequirement(id=1, text="3+ years Python", weight=0.4, must_have=True),
        JobRequirement(id=2, text="REST API experience", weight=0.3, must_have=False),
        JobRequirement(id=3, text="SQL databases", weight=0.3, must_have=False),
    ]

    results = [
        judge_requirement(resume_text, req, client)
        for req in requirements
    ]

    overall = compute_score(results, requirements)
    print(overall.score)          # e.g. 83.3
    print(overall.capped_by_must_have)  # False
"""

from .judge import judge_requirement
from .scorer import compute_score
from .schemas import (
    JobRequirement,
    LLMJudgment,
    OverallResult,
    RequirementResult,
    Verdict,
)

__all__ = [
    "judge_requirement",
    "compute_score",
    "JobRequirement",
    "LLMJudgment",
    "OverallResult",
    "RequirementResult",
    "Verdict",
]
