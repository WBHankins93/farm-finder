#!/usr/bin/env python3
"""Route every QA row to a resolution strategy and emit per-state worklists.

The taxonomy is defined in 01-database/qa-operations.md. A row's primary
strategy is the first match in priority order; rows matching nothing are
``unrouted`` and indicate blocker text that needs fixing. Outputs are derived
private artifacts under data/exports/qa-triage/; the four-file state contract
remains the only source of truth.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = ROOT / "research" / "state-expansions"
DEFAULT_OUTPUT = ROOT / "data" / "exports" / "qa-triage"
QA_STATUS = "research_or_qa_queue"
UNROUTED = "unrouted"

# Priority order matters: a row is worked under its first matching strategy.
STRATEGIES: list[tuple[str, re.Pattern[str]]] = [
    ("geography", re.compile(
        r"county requires geography review|county missing|"
        r"city or safe public service area (missing|requires review)", re.I)),
    ("corroboration", re.compile(r"single grade-E|requires corroboration", re.I)),
    ("operation_evidence", re.compile(
        r"farm-operation evidence|directory candidate|member/vendor|"
        r"production scope|farm-production evidence|"
        r"products or farm activity missing|confirm farm or agricultural-producer", re.I)),
    ("baseline", re.compile(r"baseline farm not rediscovered", re.I)),
    ("identity", re.compile(r"same normalized name|identity|contact conflict", re.I)),
    ("status_conflict", re.compile(r"operating status|closure|closed", re.I)),
    ("contact_outreach", re.compile(r"no public outreach path", re.I)),
]
STRATEGY_NAMES = [name for name, _ in STRATEGIES] + [UNROUTED]


def route(blockers: str) -> tuple[str, list[str]]:
    """Return (primary strategy, all matching strategies) for blocker text."""
    matched = [name for name, pattern in STRATEGIES if pattern.search(blockers or "")]
    if not matched:
        return UNROUTED, [UNROUTED]
    return matched[0], matched


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def triage_state(state: str, output_dir: Path | None = None) -> dict[str, Any]:
    rows = read_csv(STATE_ROOT / state / "entities.csv")
    entities = len(rows)
    qa_rows = [row for row in rows if row.get("promotion_status") == QA_STATUS]
    by_strategy: dict[str, list[dict[str, str]]] = {name: [] for name in STRATEGY_NAMES}
    for row in qa_rows:
        primary, matched = route(row.get("promotion_blockers", ""))
        by_strategy[primary].append({
            **row,
            "qa_primary_strategy": primary,
            "qa_all_strategies": "; ".join(matched),
        })
    if output_dir is not None:
        for name, bucket in by_strategy.items():
            write_csv(output_dir / state / f"{name}.csv", bucket)
    counts = {name: len(bucket) for name, bucket in by_strategy.items() if bucket}
    qa_share = round(len(qa_rows) / entities, 4) if entities else 0.0
    return {
        "state": state,
        "entities": entities,
        "qa": len(qa_rows),
        "qaShareOfEntities": qa_share,
        "flowing": qa_share < 0.20 and not by_strategy[UNROUTED],
        "strategies": dict(sorted(counts.items(), key=lambda item: -item[1])),
        "unrouted": len(by_strategy[UNROUTED]),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("states", nargs="*", help="Two-letter state codes; defaults to every committed state")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    states = [value.upper() for value in args.states] or sorted(
        path.name for path in STATE_ROOT.iterdir()
        if path.is_dir() and len(path.name) == 2 and (path / "entities.csv").is_file()
    )
    results = [triage_state(state, args.output_dir) for state in states]
    totals: dict[str, int] = {}
    for result in results:
        for name, count in result["strategies"].items():
            totals[name] = totals.get(name, 0) + count
    summary = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "qaTotal": sum(result["qa"] for result in results),
        "unroutedTotal": sum(result["unrouted"] for result in results),
        "strategyTotals": dict(sorted(totals.items(), key=lambda item: -item[1])),
        "states": results,
        "outputDir": str(args.output_dir),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
