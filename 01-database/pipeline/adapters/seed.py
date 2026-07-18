"""Seed adapter — re-emit a reviewed, hand-captured record set.

For a **capture-only** state: one whose real source can't be parsed by a live
network adapter (a magazine-layout PDF, a JS flipbook, a login-gated portal), so
its records were extracted and reviewed once, offline, and committed as a seed
file. This adapter reads that seed and yields it back, so `run.py --state <ST>`
is idempotent — it regenerates the same `data/<ST>.json` instead of overwriting
it with an empty live collection.

Seed files live **outside** `sources/*/` (e.g. `seeds/<ST>.json`) so the
`run.py --all` glob (`sources/*/[A-Z]*.json`) never mistakes one for a state
config. The source config points at it by repo-relative path:

    {"id": "...", "adapter": "seed", "path": "seeds/WV.json", "notes": "..."}

The seed holds `model.Farm.to_record()` dicts (the same shape `data/<ST>.json`
uses), so it round-trips through `Farm.from_record` with no transformation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from collect import CollectContext, adapter
from model import Farm

# adapters/ -> pipeline root; seed paths are resolved relative to it.
PIPELINE_ROOT = Path(__file__).resolve().parent.parent


@adapter("seed")
def seed(source: dict, ctx: CollectContext) -> Iterable[Farm]:
    rel = source.get("path") or source.get("url")
    if not rel:
        raise ValueError(f"seed source {source.get('id', '?')!r} has no 'path'")
    seed_path = PIPELINE_ROOT / rel
    if not seed_path.exists():
        raise FileNotFoundError(f"seed file not found: {seed_path}")
    records = json.loads(seed_path.read_text())
    for r in records:
        yield Farm.from_record(r)
