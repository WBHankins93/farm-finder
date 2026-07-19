"""QA stage — automation first, humans only on the residue.

The old pipeline gated canonical status on a human judgment for every row and
grew a routing taxonomy plus an intake cap to cope. Here QA is code that runs to
exhaustion: automated rules re-clear whatever they can, then whatever remains is
exported as the *residue* — the only thing a human ever looks at.

Add an automated rule by appending to `AUTO_RULES`. Each rule takes the full
list and returns how many rows it newly cleared.
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Callable

from cleanse import decide_eligibility
from model import Farm

AutoRule = Callable[[list[Farm]], int]


# Legacy blocker texts (from migrated rows) that are purely about geography.
_GEOGRAPHY_BLOCKERS = {
    "county requires geography review",
    "city or safe public service area requires review",
}
# Precisions that represent a real, independently-derived placement. A
# county-approx centroid must never clear a geography blocker — the centroid is
# derived from the very county assignment the blocker doubts.
_REAL_PRECISION = {"point", "address", "city"}


def _geography_only(reason: str) -> bool:
    parts = [p.strip().lower() for p in reason.split(";") if p.strip()]
    return bool(parts) and all(
        p in _GEOGRAPHY_BLOCKERS or p.startswith("missing geography") for p in parts
    )


def rule_reclear_now_geocoded(farms: list[Farm]) -> int:
    """Rows blocked *only* on geography become eligible once a real geocode has
    placed them. A real-precision coordinate (point/address/city, never a
    county-approx centroid) is independent evidence of location that resolves a
    "county requires review" blocker — the county can be derived from the point.
    Every ';'-separated blocker must be geography-flavored, so a row that also
    needs corroboration or entity-type review stays residue."""
    cleared = 0
    for f in farms:
        if f.eligible or not _geography_only(f.qa_reason):
            continue
        if f.geo.latitude is not None and f.geo.precision in _REAL_PRECISION:
            f.eligible, f.qa_reason = True, ""
            cleared += 1
    return cleared


# Official first-party grower directories. A state government's own registry is
# authoritative on "is this a real farm in this state", so a corroboration-only
# blocker on such a source is satisfied by that source alone (policy, 2026-07-18).
# National aggregators (US Farm Trail, EatWild, PickYourOwn, LocalHarvest) are
# deliberately excluded — a listing found only there still needs corroboration.
_AUTHORITATIVE_SOURCES = (
    "department of agriculture", "georgia grown", "pick tennessee", "picktn",
    "farm to you", "certified sc", "ncda", "got to be nc", "arkansas grown",
    "genuine ms", "ldaf", "kentucky proud", "go texan", "wv grown",
    "visit nc farms", "florida farm",
)


def _is_authoritative(source: str) -> bool:
    s = source.lower()
    return any(k in s for k in _AUTHORITATIVE_SOURCES)


def _is_corroboration_blocker(part: str) -> bool:
    p = part.lower()
    return "needs corroboration" in p or "directory candidate needs independent" in p


def rule_authoritative_self_corroboration(farms: list[Farm]) -> int:
    """A corroboration-only blocker is satisfied by an authoritative first-party
    source. For a residue row whose source is an official state grower directory,
    strip the corroboration blockers; clear the row if nothing else remains, else
    keep the reduced reason so any genuine remaining blocker (geography, products,
    entity type) still holds. Aggregator-only rows are untouched."""
    cleared = 0
    for f in farms:
        if f.eligible or not f.qa_reason:
            continue
        if not _is_authoritative(f.provenance.source):
            continue
        parts = [p.strip() for p in f.qa_reason.split(";") if p.strip()]
        kept = [p for p in parts if not _is_corroboration_blocker(p)]
        if len(kept) == len(parts):
            continue  # nothing corroboration-flavored to strip
        if kept:
            f.qa_reason = "; ".join(kept)
        else:
            f.eligible, f.qa_reason = True, ""
            cleared += 1
    return cleared


def rule_recompute(farms: list[Farm]) -> int:
    """Re-run the eligibility decision after upstream stages enriched records
    (dedupe merges, geo fills). Flips rows whose blocker no longer holds."""
    cleared = 0
    for f in farms:
        if not f.eligible:
            ok, reason = decide_eligibility(f)
            if ok:
                f.eligible, f.qa_reason = True, ""
                cleared += 1
            else:
                f.qa_reason = reason
    return cleared


AUTO_RULES: list[AutoRule] = [
    rule_authoritative_self_corroboration,
    rule_reclear_now_geocoded,
    rule_recompute,
]


def geography_only_residue(farms: list[Farm]) -> int:
    """Diagnostic: residue rows blocked solely on geography — the population a
    geocode backfill plus `rule_reclear_now_geocoded` can auto-clear. Reported,
    not acted on, so the migration never over-promotes on this basis."""
    return sum(1 for f in farms if not f.eligible and "geograph" in f.qa_reason.lower())


def run_qa(farms: list[Farm], residue_path: Path | None = None, rules: list[AutoRule] | None = None) -> dict:
    """Drain what automation can, export the residue, return a summary.

    `rules` defaults to `AUTO_RULES` (go-forward collection). The one-time
    migration passes `rules=[]` to *preserve prior human QA* — it partitions and
    exports the residue without auto-promoting rows a human already flagged."""
    active = AUTO_RULES if rules is None else rules
    auto_cleared = 0
    for rule in active:
        auto_cleared += rule(farms)

    residue = [f for f in farms if not f.eligible]
    reasons = Counter(f.qa_reason for f in residue)

    if residue_path is not None:
        residue_path.parent.mkdir(parents=True, exist_ok=True)
        with residue_path.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "name", "state", "county", "city", "qa_reason", "source"])
            for f in residue:
                w.writerow([f.id, f.name, f.state, f.county, f.city, f.qa_reason, f.provenance.source])

    eligible = len(farms) - len(residue)
    return {
        "total": len(farms),
        "auto_cleared": auto_cleared,
        "eligible": eligible,
        "residue": len(residue),
        "auto_clear_rate": round(eligible / len(farms), 3) if farms else 0.0,
        "geography_only_residue": geography_only_residue(farms),
        "residue_reasons": dict(reasons.most_common(12)),
    }
