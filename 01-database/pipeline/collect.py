"""Collect stage — one config-driven engine; a state is a file, not a function.

The four legacy collectors (collect_southeast/texas/alabama/mississippi.py,
~6,700 LOC of near-duplicate scraping) collapse to this: the engine walks a
state's source list from `sources/<region>/<ST>.json` and dispatches each source
to a registered *adapter* by type. Adding a state adds a config file; adding a
kind of source adds one adapter — the two axes never entangle again.

    ADAPTERS["staged"]      -> read rows already collected (migration bridge)
    ADAPTERS["csv_download"]-> Codex: fetch + map a CSV directory
    ADAPTERS["html_table"]  -> Codex: parse an HTML listing
    ADAPTERS["pdf_list"]    -> Codex: extract a PDF certificate list
    ADAPTERS["api"]         -> Codex: pull a JSON/REST source

I own the engine, the registry, and the `staged` adapter (the bridge that keeps
the existing 15,703 rows flowing while live adapters are written). Each concrete
network adapter is an isolated, parallelizable Codex task — it implements one
function against the SourceAdapter signature and never touches the engine.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Iterable

from model import Farm

# A source adapter takes a source config dict and yields raw Farm records.
SourceAdapter = Callable[[dict, "CollectContext"], Iterable[Farm]]

ADAPTERS: dict[str, SourceAdapter] = {}

# Adapter names that are part of the design but not yet implemented (Codex-owned).
# The engine skips these with a warning during the transition so a half-configured
# state still collects its working sources; a name outside this set is treated as
# a typo and hard-fails.
PLANNED_ADAPTERS = {"csv_download", "html_table", "pdf_list", "api"}


def adapter(name: str) -> Callable[[SourceAdapter], SourceAdapter]:
    def register(fn: SourceAdapter) -> SourceAdapter:
        ADAPTERS[name] = fn
        return fn
    return register


class CollectContext:
    """Everything an adapter needs beyond its own source config: the state code,
    region, and a handle to already-migrated canonical rows (for the staged
    bridge). Kept tiny on purpose."""

    def __init__(self, state: str, region: str, staged: dict[str, list[Farm]] | None = None):
        self.state = state
        self.region = region
        self.staged = staged or {}
        self.warnings: list[str] = []


@adapter("staged")
def staged_adapter(source: dict, ctx: CollectContext) -> Iterable[Farm]:
    """Bridge adapter: emit the canonical rows already migrated for this state.
    Lets the engine run end-to-end today while live adapters are authored. When
    a state's live adapters exist, drop the `staged` source from its config."""
    return ctx.staged.get(ctx.state, [])


def load_state_config(path: Path) -> dict:
    cfg = json.loads(path.read_text())
    for key in ("state", "region", "sources"):
        if key not in cfg:
            raise ValueError(f"{path}: source config missing required key '{key}'")
    return cfg


def collect_state(config: dict, ctx: CollectContext) -> list[Farm]:
    """Run every source in a state's config through its adapter and concatenate.
    Unknown adapters are skipped with a clear error rather than crashing the run —
    a half-configured state should still collect its working sources."""
    out: list[Farm] = []
    for source in config.get("sources", []):
        kind = source.get("adapter", "staged")
        fn = ADAPTERS.get(kind)
        label = source.get("name", source.get("id", "?"))
        if fn is None:
            if kind in PLANNED_ADAPTERS:
                ctx.warnings.append(f"[{config['state']}] skipped {kind} source (not yet built): {label}")
                continue
            raise NotImplementedError(
                f"[{config['state']}] unknown adapter type {kind!r} (source: {label}). "
                f"Expected one of {sorted(set(ADAPTERS) | PLANNED_ADAPTERS)}."
            )
        out.extend(fn(source, ctx))
    return out
