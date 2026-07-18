"""Scaffold per-state source configs from the existing state.yaml files.

The 10 already-collected states carry their real source lists inside
`research/state-expansions/<ST>/state.yaml` (`collection.sources`). This turns
"hand-port 10 states" into one command: it emits `sources/<region>/<ST>.json`
for each, pre-mapping recognizable source types to adapters and defaulting the
rest to `staged` so the engine keeps running end-to-end.

Codex then upgrades adapters state-by-state and authors configs for new states
against sources/SCHEMA.md. Safe to re-run; it overwrites only scaffolded files.

    python3 01-database/pipeline/scaffold_sources.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EXPANSIONS = ROOT / "research" / "state-expansions"
SOURCES = HERE / "sources"


def guess_adapter(source: dict) -> str:
    """Best-effort adapter guess from the source url/name. Defaults to `staged`
    (the working bridge) so nothing breaks; Codex refines these."""
    hay = f"{source.get('sourceUrl', '')} {source.get('name', '')}".lower()
    if hay.endswith(".pdf") or ".pdf" in hay or "certificate" in hay or "permit" in hay:
        return "pdf_list"
    if ".csv" in hay or "download" in hay:
        return "csv_download"
    if "/api" in hay or "api." in hay or "json" in hay:
        return "api"
    if source.get("sourceUrl"):
        return "html_table"
    return "staged"


def load_region_map() -> dict[str, str]:
    data = json.loads((HERE / "regions.json").read_text())
    return {st: name for name, r in data["regions"].items() for st in r["states"]}


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "source"


def run() -> list[str]:
    region_map = load_region_map()
    written: list[str] = []
    for state_yaml in sorted(EXPANSIONS.glob("*/state.yaml")):
        data = json.loads(state_yaml.read_text())  # state.yaml is JSON content
        st = data["state"]["code"]
        region = region_map.get(st, "unassigned")
        sources = []
        seen: set[str] = set()
        # Always keep a staged bridge so the engine runs before live adapters exist.
        sources.append({"id": "staged-bridge", "name": "Migrated canonical rows (bridge)",
                        "url": "", "adapter": "staged",
                        "notes": "Remove once live adapters cover this state."})
        for s in data.get("collection", {}).get("sources", []):
            sid = s.get("sourceId") or slug(s.get("name", "source"))
            if sid in seen:
                continue
            seen.add(sid)
            sources.append({
                "id": sid,
                "name": s.get("name", ""),
                "url": s.get("sourceUrl", "") or "",
                "adapter": guess_adapter(s),
                "notes": (s.get("notes", "") or "")[:200],
            })
        cfg = {
            "state": st,
            "name": data["state"].get("name", st),
            "region": region,
            "countyEquivalentLabel": data["state"].get("countyEquivalentLabel", "county"),
            "sources": sources,
        }
        out = SOURCES / region / f"{st}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
        written.append(str(out.relative_to(HERE)))
    return written


if __name__ == "__main__":
    files = run()
    print(f"Scaffolded {len(files)} state source configs:")
    for f in files:
        print("  ", f)
