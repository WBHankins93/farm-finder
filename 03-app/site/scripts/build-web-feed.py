#!/usr/bin/env python3
"""Generate the app's runtime feed (public/farms.json) from the pipeline output.

Reads the eligible, privacy-cleared feed the pipeline publishes
(01-database/pipeline/build/app-farms.json, produced by `run.py --publish`) and
writes a minified copy the web client fetches at runtime. Regenerable; the file
is git-ignored — the committed source of truth is the pipeline's per-state data.

    python3 scripts/build-web-feed.py
"""
import json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[2] / "01-database" / "pipeline" / "build" / "app-farms.json"
OUT = HERE.parent / "public" / "farms.json"

def main() -> int:
    if not SRC.exists():
        print(f"missing {SRC} — run: python3 01-database/pipeline/run.py --publish", file=sys.stderr)
        return 1
    feed = json.loads(SRC.read_text())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(feed, separators=(",", ":"), ensure_ascii=False))
    print(f"wrote {OUT.relative_to(HERE.parent)} — {len(feed)} farms, {OUT.stat().st_size/1e6:.1f} MB")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
