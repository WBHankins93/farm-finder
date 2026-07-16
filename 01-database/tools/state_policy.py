#!/usr/bin/env python3
"""Shared FarmFinder candidate-retention and exclusion policy.

Collectors may discover only a farm name. That is still a durable candidate.
Missing fields create research blockers; they never create an exclusion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


RESEARCH_STATUS = "research_or_qa_queue"
ELIGIBLE_STATUS = "promotion_eligible_reviewed"
EXCLUDED_STATUS = "excluded_affirmative_evidence"

AFFIRMATIVE_EXCLUSION_REASONS = frozenset({
    "confirmed_nonfarm",
    "confirmed_closed",
    "outside_jurisdiction",
    "duplicate_identity",
})

# Ingestion tiers classify a source before collection so low-signal registries
# corroborate existing candidates instead of creating open-ended QA debt.
# See 01-database/pipeline-enrichment-plan.md section 4.
SOURCE_TIERS = frozenset({"candidate", "identity_hint", "excluded_source"})


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


def sufficient_promotion_evidence(
    observation_grades: str,
    decision_grades: Iterable[str] = (),
) -> bool:
    """Eligibility needs evidence beyond a single unresolved grade-E listing.

    Grade F observations block promotion outright. Grade-E-only observation
    evidence passes only when an append-only corroborate/correct decision
    contributes grade A-D evidence for the same candidate.
    """
    observed = {grade.strip() for grade in observation_grades.split(";") if grade.strip()}
    if "F" in observed:
        return False
    corroborated = {grade.strip() for grade in decision_grades if grade.strip() in {"A", "B", "C", "D"}}
    return (observed | corroborated) != {"E"}


def source_tier_issues(sources: Iterable[Mapping[str, object]]) -> tuple[list[str], list[str]]:
    """Return (invalid, untiered) source IDs under the ingestion-tier policy.

    Invalid tiers are contract errors. Untiered sources are legacy plans that
    predate the policy; they warn until the state is next recollected.
    """
    invalid: list[str] = []
    untiered: list[str] = []
    for row in sources:
        tier = row.get("tier")
        source_id = str(row.get("sourceId"))
        if tier is None:
            untiered.append(source_id)
        elif tier not in SOURCE_TIERS:
            invalid.append(source_id)
    return invalid, untiered


def validate_exclusion_reason(reason: str) -> None:
    """Reject absence-based or undocumented exclusion decisions."""
    if reason not in AFFIRMATIVE_EXCLUSION_REASONS:
        raise ValueError(
            "exclude decisions require one of: "
            + ", ".join(sorted(AFFIRMATIVE_EXCLUSION_REASONS))
        )


def effective_decisions(rows: Iterable[Mapping[str, str]]) -> list[Mapping[str, str]]:
    """Return unsuperseded decisions while validating the append-only chain."""
    materialized = list(rows)
    identifiers = [row.get("review_id", "") for row in materialized]
    if not all(identifiers) or len(identifiers) != len(set(identifiers)):
        raise ValueError("decision review IDs must be present and unique")
    known = set(identifiers)
    superseded: set[str] = set()
    supersedes_by_id: dict[str, str] = {}
    for row in materialized:
        prior = row.get("supersedes_review_id", "").strip()
        if not prior:
            continue
        if prior == row.get("review_id"):
            raise ValueError(f"decision {prior} cannot supersede itself")
        if prior not in known:
            raise ValueError(f"decision {row.get('review_id')} supersedes unknown decision {prior}")
        if prior in superseded:
            raise ValueError(f"decision {prior} is superseded more than once")
        superseded.add(prior)
        supersedes_by_id[row.get("review_id", "")] = prior

    # A cycle would make every member appear superseded and silently remove the
    # entire chain from the effective view. Reject it as an invalid append-only
    # history instead.
    for identifier in identifiers:
        seen: set[str] = set()
        current = identifier
        while current in supersedes_by_id:
            if current in seen:
                raise ValueError(f"decision supersession cycle includes {current}")
            seen.add(current)
            current = supersedes_by_id[current]
    return [row for row in materialized if row.get("review_id") not in superseded]
