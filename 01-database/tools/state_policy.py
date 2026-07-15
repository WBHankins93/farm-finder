#!/usr/bin/env python3
"""Shared FarmFinder candidate-retention and exclusion policy.

Collectors may discover only a farm name. That is still a durable candidate.
Missing fields create research blockers; they never create an exclusion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


RESEARCH_STATUS = "research_or_qa_queue"
ELIGIBLE_STATUS = "promotion_eligible_reviewed"
EXCLUDED_STATUS = "excluded_affirmative_evidence"

AFFIRMATIVE_EXCLUSION_REASONS = frozenset({
    "confirmed_nonfarm",
    "confirmed_closed",
    "outside_jurisdiction",
    "duplicate_identity",
})


@dataclass(frozen=True)
class CandidateDisposition:
    status: str
    blockers: tuple[str, ...]
    exclusion_reason: str = ""


def classify_candidate(
    farm_name: str,
    blockers: Iterable[str] = (),
    *,
    exclusion_reason: str = "",
) -> CandidateDisposition:
    """Return a deterministic disposition without treating nulls as exclusions."""
    if not farm_name.strip():
        raise ValueError("a candidate requires at least a farm name")
    normalized_blockers = tuple(dict.fromkeys(value.strip() for value in blockers if value.strip()))
    if exclusion_reason:
        if exclusion_reason not in AFFIRMATIVE_EXCLUSION_REASONS:
            raise ValueError(
                f"{exclusion_reason!r} is not an affirmative exclusion reason; "
                "missing data must remain in research_or_qa_queue"
            )
        return CandidateDisposition(EXCLUDED_STATUS, normalized_blockers, exclusion_reason)
    if normalized_blockers:
        return CandidateDisposition(RESEARCH_STATUS, normalized_blockers)
    return CandidateDisposition(ELIGIBLE_STATUS, ())


def validate_exclusion_reason(reason: str) -> None:
    """Reject absence-based or undocumented exclusion decisions."""
    if reason not in AFFIRMATIVE_EXCLUSION_REASONS:
        raise ValueError(
            "exclude decisions require one of: "
            + ", ".join(sorted(AFFIRMATIVE_EXCLUSION_REASONS))
        )
