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

from model import Farm


def to_app_records(farms: list[Farm], eligible_only: bool = True) -> list[dict]:
    rows = [f for f in farms if f.eligible] if eligible_only else list(farms)
    rows.sort(key=lambda f: (f.state, f.name.lower()))
    return [f.to_app_record() for f in rows]


def write_app_json(farms: list[Farm], path: Path, eligible_only: bool = True) -> dict:
    records = to_app_records(farms, eligible_only=eligible_only)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n")
    return {
        "written": len(records),
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
