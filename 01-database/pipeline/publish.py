"""Publish stage — emit the product's data from eligible, cleared records.

Two sinks:
  * `write_app_json`  — the file the web/app directory reads (the shape in
                        03-app/site/app/lib/farms.ts). This is what lights up the
                        map today.
  * `load_postgres`   — the cutover sink (interface only; implemented at the
                        Postgres-cutover step). Kept here so the contract is one
                        place.

Publish is where privacy is enforced: only `Contact.public_string()` output
reaches the app record, and only geocoded rows are marked mappable.
"""
from __future__ import annotations

import json
from pathlib import Path

from cleanse import aggregate_dedupe, near_duplicate_clusters
from model import Farm


def to_app_records(farms: list[Farm], eligible_only: bool = True) -> tuple[list[dict], int]:
    """Build the app feed. Applies a feed-level safety-net dedupe across all
    states, then sorts. Returns (records, merged_count)."""
    rows = [f for f in farms if f.eligible] if eligible_only else list(farms)
    rows, merged = aggregate_dedupe(rows)
    rows.sort(key=lambda f: (f.state, f.name.lower()))
    return [f.to_app_record() for f in rows], merged


def write_app_json(farms: list[Farm], path: Path, eligible_only: bool = True) -> dict:
    records, merged = to_app_records(farms, eligible_only=eligible_only)
    near_dups = near_duplicate_clusters([f for f in farms if not eligible_only or f.eligible])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n")
    return {
        "written": len(records),
        "cross_file_merged": merged,
        "near_dup_clusters": near_dups,
        "mappable": sum(1 for r in records if r["geoPrecision"] != "ungeocoded"),
        "with_contact": sum(1 for r in records if r["contact"]),
        "path": str(path),
    }


def load_postgres(farms: list[Farm], dsn: str) -> None:  # pragma: no cover
    """Cutover sink. Implemented at the Postgres-cutover step against the same
    canonical model. Left as an explicit NotImplemented so nobody assumes the
    app is reading Postgres before the cutover actually happens."""
    raise NotImplementedError(
        "Postgres cutover is a later, gated step — see "
        "03-app/site/docs/data-governance/cutover-runbook.md"
    )
