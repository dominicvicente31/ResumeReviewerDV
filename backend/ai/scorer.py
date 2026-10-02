"""
Deterministic score aggregation — no LLM involved.

Scoring rules (all code, fully reproducible):
  - met     → 100 % of the requirement's weight
  - partial → PARTIAL_STRICT..PARTIAL_LENIENT of the weight, depending on how
              many requirements the profile has (see _partial_fraction)
  - not_met → 0 % of the requirement's weight
  - A met/partial verdict whose evidence quote can't be found in the resume
    earns only UNVERIFIED_EVIDENCE_FACTOR of the credit it would have had.
  - If any must-have requirement is not_met, the final score is capped at
    MUST_HAVE_CAP; if one is only partial, at MUST_HAVE_PARTIAL_CAP.
"""

from .schemas import JobRequirement, OverallResult, RequirementResult, Verdict

# Partial credit grows with the number of requirements: a short list should be
# met almost entirely, while a long list is unlikely to be met in full, so
# near-misses count for more.
PARTIAL_STRICT = 0.3     # partial credit when a profile has <= STRICT_UP_TO requirements
PARTIAL_LENIENT = 0.5    # partial credit when a profile has >= LENIENT_FROM requirements
STRICT_UP_TO = 3
LENIENT_FROM = 10

UNVERIFIED_EVIDENCE_FACTOR = 0.85  # mild penalty when the quoted evidence isn't in the resume

MUST_HAVE_CAP = 50.0         # maximum score when a must-have requirement is not met
MUST_HAVE_PARTIAL_CAP = 75.0  # maximum score when a must-have requirement is only partial


def _partial_fraction(num_requirements: int) -> float:
    """Linearly interpolate partial credit between the strict and lenient ends."""
    if num_requirements <= STRICT_UP_TO:
        return PARTIAL_STRICT
    if num_requirements >= LENIENT_FROM:
        return PARTIAL_LENIENT
    span = LENIENT_FROM - STRICT_UP_TO
    t = (num_requirements - STRICT_UP_TO) / span
    return PARTIAL_STRICT + t * (PARTIAL_LENIENT - PARTIAL_STRICT)


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

    verdict_fraction = {
        Verdict.MET: 1.0,
        Verdict.PARTIAL: _partial_fraction(len(requirements)),
        Verdict.NOT_MET: 0.0,
    }

    weighted_sum = 0.0
    must_have_missed = False
    must_have_partial = False

    for result in results:
        req = req_map.get(result.requirement_id)
        if req is None:
            continue
        credit = verdict_fraction[result.verdict]
        if result.verdict != Verdict.NOT_MET and not result.evidence_verified:
            credit *= UNVERIFIED_EVIDENCE_FACTOR
        weighted_sum += req.weight * credit
        if req.must_have and result.verdict == Verdict.NOT_MET:
            must_have_missed = True
        elif req.must_have and result.verdict == Verdict.PARTIAL:
            must_have_partial = True

    score = (weighted_sum / total_weight) * 100.0
    capped_by_must_have = must_have_missed
    if must_have_missed:
        score = min(score, MUST_HAVE_CAP)
    elif must_have_partial and score > MUST_HAVE_PARTIAL_CAP:
        score = MUST_HAVE_PARTIAL_CAP
        capped_by_must_have = True

    return OverallResult(
        score=round(score, 1),
        capped_by_must_have=capped_by_must_have,
        per_requirement=results,
    )
