#!/usr/bin/env python3
"""Assess a prospective PR before publication and reject artifact-heavy dumps."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATE_CONTRACT_FILES = {
    "state.yaml", "entities.csv", "decisions.csv", "report.md",
}
PROHIBITED_STATE_NAMES = {
    "state-config.json", "sources.json", "manual-decisions.csv",
    "county-coverage.csv", "completion-report.md", "release-manifest.json",
    "raw-source-records.json", "source-pass-log.json", "collection-summary.json",
    "qa-queue.csv", "identity-review.csv", "excluded-observations.csv",
    "county-lookup-errors.json", "geography-conflicts.csv",
}
# New-state collection pauses while the committed QA queue is over budget.
# See 01-database/qa-operations.md; the reviewed exception is the existing
# large-reviewed-change label, which skips this gate entirely in CI.
# Post-burn-down judgment-only residue is 24 rows: 21 canonical-baseline
# research items and 3 unresolved status cases. Keep intake at 1.5x that
# human-review floor (ceil(1.5 * 24) = 36); automated queues are tracked
# separately.
QA_INTAKE_CAP = 36


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--max-files", type=int, default=20)
    parser.add_argument("--max-additions", type=int, default=15000)
    return parser.parse_args()


def run(*args: str) -> str:
    return subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True).stdout


def stale_state_directories(merge_base: str, base: str, states, runner=run) -> list[str]:
    """States whose committed release changed on the base branch after this
    branch diverged. Applying a batch on top of a superseded release forks the
    append-only history, so these must be rebased before review."""
    stale = []
    for state in sorted(states):
        directory = f"research/state-expansions/{state}"
        newer = runner("git", "rev-list", "-1", f"{merge_base}..{base}", "--", directory).strip()
        if newer:
            stale.append(state)
    return stale


def new_state_directories(merge_base: str, states, runner=run) -> list[str]:
    """States in this PR that did not exist at the merge-base."""
    added = []
    for state in sorted(states):
        existing = runner("git", "ls-tree", merge_base, "--name-only",
                          f"research/state-expansions/{state}").strip()
        if not existing:
            added.append(state)
    return added


def committed_qa_total(exclude=(), root: Path = ROOT) -> int:
    """Sum researchOrQaEntities across committed contract-v2 states."""
    total = 0
    for path in sorted((root / "research" / "state-expansions").glob("*/state.yaml")):
        if path.parent.name in exclude:
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        total += int(document.get("release", {}).get("counts", {}).get("researchOrQaEntities", 0))
    return total


def main() -> int:
    args = parse_args()
    merge_base = run("git", "merge-base", args.base, args.head).strip()
    output = run("git", "diff", "--numstat", f"{merge_base}..{args.head}")
    files = []
    errors: list[str] = []
    warnings: list[str] = []
    additions = 0
    deletions = 0
    states: dict[str, set[str]] = {}
    for line in output.splitlines():
        added, deleted, path = line.split("\t", 2)
        added_count = int(added) if added.isdigit() else 0
        deleted_count = int(deleted) if deleted.isdigit() else 0
        additions += added_count
        deletions += deleted_count
        files.append({"path": path, "additions": added_count, "deletions": deleted_count})
        parts = Path(path).parts
        if len(parts) >= 4 and parts[:2] == ("research", "state-expansions"):
            state, filename = parts[2], parts[3]
            if added_count:
                states.setdefault(state, set()).add(filename)
            if added_count and filename not in STATE_CONTRACT_FILES:
                errors.append(f"{state} changes non-contract state file {filename}")
            if added_count and filename in PROHIBITED_STATE_NAMES:
                errors.append(f"{state} includes prohibited generated artifact {filename}")
        if added_count > 5000:
            warnings.append(f"large text addition: {path} adds {added_count} lines")

    if len(files) > args.max_files:
        errors.append(f"PR changes {len(files)} files; limit is {args.max_files}")
    if additions > args.max_additions:
        errors.append(f"PR adds {additions} lines; limit is {args.max_additions}")
    for state, names in states.items():
        if len(names) > len(STATE_CONTRACT_FILES):
            errors.append(f"{state} changes {len(names)} state files; contract permits four")
    for state in stale_state_directories(merge_base, args.base, states):
        errors.append(
            f"{state} release changed on {args.base} after this branch's merge-base; "
            "rebase onto the latest main before opening the PR"
        )
    added_states = new_state_directories(merge_base, states)
    if added_states:
        backlog = committed_qa_total(exclude=set(added_states))
        if backlog > QA_INTAKE_CAP:
            errors.append(
                f"new-state collection ({', '.join(added_states)}) is paused: the committed QA "
                f"queue is {backlog}, above the {QA_INTAKE_CAP} intake cap (qa-operations.md); "
                "reduce QA first or request the large-reviewed-change exception"
            )

    files.sort(key=lambda row: (row["additions"], row["deletions"]), reverse=True)
    report = {
        "status": "passed" if not errors else "failed",
        "base": args.base,
        "head": args.head,
        "mergeBase": merge_base,
        "totals": {"files": len(files), "additions": additions, "deletions": deletions},
        "stateFiles": {state: sorted(names) for state, names in sorted(states.items())},
        "largestChanges": files[:10],
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
