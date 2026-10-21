"""Orchestrator — run a state config through the live engine and publish.

This is the piece that makes the adapters real. `migrate.py` was a one-time
bridge that read `entities.csv`; `run.py` runs the actual pipeline
(collect → cleanse → geo → qa → publish) from a state's source config, so newly
authored states (KY/VA/WV) and wired existing states collect live data.

    run.py --state KY        # collect one state -> data/KY.json
    run.py --all             # every state that has a source config
    run.py --publish         # aggregate all states -> build/app-farms.json
    run.py --state KY --publish

Canonical store: a state that has been collected lives in
`01-database/pipeline/data/<ST>.json` (committed — the new source of truth).
A state not yet collected falls back to the `entities.csv` migration bridge at
publish time, so the app always reflects every state either way. The transition
is per-state: when a state's live adapters cover it, commit its data file and
retire its `entities.csv`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import migrate  # noqa: E402
from cleanse import CATEGORIES, classify_category, decide_eligibility  # noqa: E402
from collect import CollectContext, collect_state, load_state_config  # noqa: E402
from geo import apply_geo_fallback  # noqa: E402
from migrate import EXPANSIONS, assign_ids, dedupe_preserving_qa, integrity_demote, load_region_map  # noqa: E402
from model import Farm  # noqa: E402
from privacy import apply_privacy  # noqa: E402
from publish import write_app_json  # noqa: E402
from qa import rule_authoritative_self_corroboration, rule_reclear_now_geocoded, run_qa  # noqa: E402

DATA = HERE / "data"
BUILD = HERE / "build"
SOURCES = HERE / "sources"


def find_config(state: str) -> Path | None:
    hits = sorted(SOURCES.glob(f"*/{state}.json"))
    return hits[0] if hits else None


def _staged_bridge(state: str, region_map: dict) -> list[Farm]:
    """Existing canonical rows for a state (empty for a brand-new state), fed to
    the `staged` adapter so wiring live sources augments rather than replaces."""
    if (EXPANSIONS / state / "entities.csv").exists():
        return migrate.build_state_canonical(state, region_map)
    return []


def _finalize(farms: list[Farm], state: str) -> dict:
    """cleanse -> geo -> qa on one state's collected rows, preserving prior human
    QA on bridged rows and deciding eligibility only for freshly collected ones."""
    for f in farms:
        if f.category not in CATEGORIES or f.category == "Mixed":
            f.category = classify_category(f.products_text)
    farms, merged = dedupe_preserving_qa(farms)
    assign_ids(farms)
    integrity_demote(farms)
    # A fresh live row has no decision yet (eligible False, no qa_reason); a
    # bridged row already carries its preserved decision — leave it alone.
    for f in farms:
        if not f.eligible and not f.qa_reason:
            f.eligible, f.qa_reason = decide_eligibility(f)
    geo_stats = apply_geo_fallback(farms)
    apply_privacy(farms)
    BUILD.mkdir(parents=True, exist_ok=True)
    qa_stats = run_qa(
        farms,
        residue_path=BUILD / f"qa-residue-{state}.csv",
        rules=[rule_authoritative_self_corroboration, rule_reclear_now_geocoded],
    )
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / f"{state}.json").write_text(
        json.dumps([f.to_record() for f in farms], indent=2, ensure_ascii=False) + "\n"
    )
    return {"merged": merged, "geo": geo_stats, "qa": qa_stats, "count": len(farms)}


def run_state(state: str) -> dict:
    cfg_path = find_config(state)
    if cfg_path is None:
        raise SystemExit(f"no source config found: sources/*/{state}.json")
    region_map = load_region_map()
    cfg = load_state_config(cfg_path)
    ctx = CollectContext(state=state, region=cfg["region"], staged={state: _staged_bridge(state, region_map)})
    collected = collect_state(cfg, ctx)
    live = sum(1 for s in cfg["sources"] if s.get("adapter") not in (None, "staged"))
    stats = _finalize(collected, state)
    stats["live_sources"] = live
    stats["bridged"] = len(ctx.staged.get(state, []))
    stats["warnings"] = ctx.warnings
    return stats


def _validate_state_code(state: str) -> str:
    if not re.fullmatch(r"[A-Za-z]{2}", state, flags=re.ASCII):
        raise SystemExit("state must be a two-letter ASCII code")
    return state.upper()


def _sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def propose_state(state: str) -> dict:
    """Collect isolated source observations without finalizing or writing canonical data."""
    state = _validate_state_code(state)
    cfg_path = find_config(state)
    if cfg_path is None:
        raise SystemExit(f"no source config found: sources/*/{state}.json")
    cfg = load_state_config(cfg_path)
    canonical_path = DATA / f"{state}.json"
    base_hash = _sha256_file(canonical_path)
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    config_hash = hashlib.sha256(cfg_path.read_bytes()).hexdigest()
    ctx = CollectContext(state=state, region=cfg["region"])
    collect_state(cfg, ctx)

    run_id = uuid4().hex
    proposal = {
        "schema_version": 1,
        "proposal_id": run_id,
        "state": state,
        "fetched_at": fetched_at,
        "config_sha256": config_hash,
        "base_canonical_sha256": base_hash,
        "artifact_classification": "internal_only",
        "pagination_boundary": "iterator_exhaustion_does_not_verify_remote_pagination_completeness",
        "source_outcomes": ctx.source_outcomes,
        "observations": ctx.source_observations,
    }
    proposal_dir = BUILD / "proposals"
    proposal_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(proposal_dir, 0o700)
    proposal_path = proposal_dir / f"{state}-{run_id}.json"
    descriptor = os.open(proposal_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(json.dumps(proposal, indent=2, ensure_ascii=False) + "\n")
    return {
        "proposal_path": proposal_path,
        "source_outcomes": ctx.source_outcomes,
        "required_failures": [
            outcome["source_id"] for outcome in ctx.source_outcomes
            if outcome["required"] and outcome["status"] in ("failed", "partial", "disabled")
        ],
        "warnings": ctx.warnings,
    }


def publish_all() -> dict:
    """Aggregate every state and write the app feed. A committed data/<ST>.json
    (live-collected) supersedes the entities.csv bridge for that state."""
    region_map = load_region_map()
    migrate.run()  # refresh the bridge baseline in build/canonical.json
    canon = json.loads((BUILD / "canonical.json").read_text())
    by_state: dict[str, list[Farm]] = defaultdict(list)
    for r in canon:
        by_state[r["state"]].append(Farm.from_record(r))
    for data in sorted(DATA.glob("*.json")):
        by_state[data.stem] = [Farm.from_record(r) for r in json.loads(data.read_text())]
    farms = [f for rows in by_state.values() for f in rows]
    stats = write_app_json(farms, BUILD / "app-farms.json", eligible_only=True)
    stats["states"] = len(by_state)
    stats["live_states"] = sorted(p.stem for p in DATA.glob("*.json"))
    return stats


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state", help="two-letter state code to collect")
    p.add_argument("--all", action="store_true", help="collect every state with a source config")
    p.add_argument("--publish", action="store_true", help="aggregate all states into the app feed")
    p.add_argument("--dry-run", action="store_true", help="write an inspectable source proposal without changing canonical data")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.state:
        args.state = _validate_state_code(args.state)
    if args.dry_run and (not args.state or args.all or args.publish):
        raise SystemExit("--dry-run requires --state <ST> and cannot be combined with --all or --publish")
    if not (args.state or args.all or args.publish):
        raise SystemExit("nothing to do: pass --state <ST>, --all, or --publish")
    if args.dry_run:
        result = propose_state(args.state)
        print(f"proposal: {result['proposal_path']}")
        for outcome in result["source_outcomes"]:
            print(f"  {outcome['source_id']}: {outcome['status']} ({outcome['row_count']} rows)")
        for w in result["warnings"]:
            print(" ", w)
        if result["required_failures"]:
            print("required source outcomes need attention: " + ", ".join(result["required_failures"]))
            return 1
    elif args.all:
        for cfg in sorted(SOURCES.glob("*/[A-Z]*.json")):
            st = cfg.stem
            s = run_state(st)
            print(f"{st}: collected {s['count']} ({s['bridged']} bridged, {s['live_sources']} live sources)"
                  + (f"  · {len(s['warnings'])} skipped" if s["warnings"] else ""))
    elif args.state:
        s = run_state(args.state)
        print(f"{args.state}: collected {s['count']} rows "
              f"({s['bridged']} bridged + live) · eligible {s['qa']['eligible']} · residue {s['qa']['residue']}")
        for w in s["warnings"]:
            print(" ", w)
        print(f"  -> data/{args.state}.json")
    if args.publish:
        s = publish_all()
        print(f"published {s['written']} farms across {s['states']} states "
              f"({s['mappable']} mappable); live states: {', '.join(s['live_states']) or 'none yet'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
