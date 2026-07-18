"""Shared HTTP fetch for source adapters — sends a browser User-Agent.

Many public producer directories (U.S. Farm Trail, PickYourOwn, EatWild, and
others) return `403 Forbidden` to the default `Python-urllib/x.y` User-Agent, so
an adapter fetching with a bare `urllib.request.urlopen` collects nothing and the
engine records a source failure. Routing every adapter fetch through here sends a
consistent browser UA; behavior is otherwise identical to `urlopen` (returns the
same response object), so callers keep reading `.read()` / charset as before.
"""
from __future__ import annotations

import urllib.request

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def urlopen(url: str, timeout: int = 30):
    """`urllib.request.urlopen` with a browser User-Agent."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    return urllib.request.urlopen(req, timeout=timeout)
