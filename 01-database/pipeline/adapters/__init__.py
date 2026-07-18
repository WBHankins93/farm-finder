"""Adapter package — one module per source type, auto-discovered by the engine.

Drop a module in this directory and it registers itself; no engine edits, no
shared files between adapter PRs. Each module implements exactly one source
type against the SourceAdapter signature:

    # adapters/pdf_list.py
    from collect import adapter, CollectContext
    from model import Farm

    @adapter("pdf_list")
    def pdf_list(source: dict, ctx: CollectContext):
        ...fetch source["url"], parse, yield Farm(...)

`collect.collect_state()` calls `load_all()` lazily on first use, importing
every module here so the decorators run. Modules whose names start with `_`
are skipped (scratch/helpers).
"""
from __future__ import annotations

from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules


def load_all() -> list[str]:
    loaded: list[str] = []
    for mod in iter_modules([str(Path(__file__).resolve().parent)]):
        if mod.name.startswith("_"):
            continue
        import_module(f"{__name__}.{mod.name}")
        loaded.append(mod.name)
    return loaded
