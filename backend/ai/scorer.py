"""
Deterministic score aggregation — no LLM involved.

Scoring rules (all code, fully reproducible):
  - met     → 100 % of the requirement's weight
  - partial → 50 % of the requirement's weight
  - not_met → 0 % of the requirement's weight
  - If any must-have requirement is not_met, the final score is capped at
    MUST_HAVE_CAP regardless of how well other requirements are met.
"""

from .schemas import JobRequirement, OverallResult, RequirementResult, Verdict

_VERDICT_FRACTION: dict[Verdict, float] = {
    Verdict.MET: 1.0,
    Verdict.PARTIAL: 0.5,
    Verdict.NOT_MET: 0.0,
}

MUST_HAVE_CAP = 50.0  # maximum score when a must-have requirement is not met


def compute_score(
    results: list[RequirementResult],
    requirements: list[JobRequirement],
) -> OverallResult:
    """
    Aggregate per-requirement judgments into an overall alignment score.

    Parameters
    ----------
    results:
        Output from judge_requirement() for each requirement.
    requirements:
        The job requirements (used for weights and must-have flags).

    Returns
    -------
    OverallResult with a 0–100 score.
    """
    req_map = {r.id: r for r in requirements}
    total_weight = sum(r.weight for r in requirements)

    if total_weight == 0:
        return OverallResult(
            score=0.0,
            capped_by_must_have=False,
            per_requirement=results,
        )

    weighted_sum = 0.0
    capped_by_must_have = False

    for result in results:
        req = req_map.get(result.requirement_id)
        if req is None:
            continue
        weighted_sum += req.weight * _VERDICT_FRACTION[result.verdict]
        if req.must_have and result.verdict == Verdict.NOT_MET:
            capped_by_must_have = True

    score = (weighted_sum / total_weight) * 100.0
    if capped_by_must_have:
        score = min(score, MUST_HAVE_CAP)

    return OverallResult(
        score=round(score, 1),
        capped_by_must_have=capped_by_must_have,
        per_requirement=results,
    )
