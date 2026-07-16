#!/usr/bin/env python3
"""Capture reproducible owned-website evidence for staged state candidates.

Reachability alone supports only a likely-operating classification. A stronger
current-year signal requires a 2025/2026 date near active sales, season, ordering,
harvest, visiting, or availability language. Missing or blocked sites remain
unresolved and never become closure evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import ssl
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
USER_AGENT = "FarmFinderDataAudit/1.0 (+https://github.com/farmfinder)"
ACTIVE_SIGNAL = re.compile(
    r"\b(?:open|opening|order|orders|ordering|season|available|availability|harvest|"
    r"pickup|pick-up|farm stand|farmstand|farmers market|CSA|visit|hours|shipping|delivery)\b",
    re.I,
)
CLOSURE_SIGNAL = re.compile(
    r"\b(?:permanently closed|ceased operations|closed (?:our|its) doors|"
    r"no longer (?:in business|operating)|out of business)\b",
    re.I,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    parser.add_argument("--workers", type=int, default=16)
    return parser.parse_args()


def clean_page(body: bytes) -> str:
    text = body.decode("utf-8", errors="replace")
    text = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", text, flags=re.I | re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def dated_active_excerpt(text: str) -> tuple[str, str]:
    for match in re.finditer(r"\b(202[56])\b", text):
        excerpt = text[max(0, match.start() - 240):match.end() + 240]
        if ACTIVE_SIGNAL.search(excerpt):
            return match.group(1), excerpt[:500]
    return "", ""


def fetch(url: str) -> dict[str, Any]:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.8"})
    try:
        context = ssl.create_default_context()
        with urllib.request.urlopen(request, timeout=18, context=context) as response:
            body = response.read(1_500_000)
            final_url = response.geturl()
            status = int(getattr(response, "status", 200))
            content_type = response.headers.get("Content-Type", "")
        text = clean_page(body) if "html" in content_type.casefold() or not content_type else ""
        current_year, excerpt = dated_active_excerpt(text)
        closure = CLOSURE_SIGNAL.search(text)
        return {
            "requestedUrl": url,
            "finalUrl": final_url,
            "httpStatus": status,
            "retrievedAt": retrieved_at,
            "responseSha256": hashlib.sha256(body).hexdigest(),
            "contentType": content_type,
            "reachable": 200 <= status < 400,
            "currentYearActiveSignal": current_year,
            "activeEvidenceExcerpt": excerpt,
            "explicitClosureSignal": closure.group(0) if closure else "",
            "error": "",
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
        return {
            "requestedUrl": url,
            "finalUrl": "",
            "httpStatus": int(getattr(exc, "code", 0) or 0),
            "retrievedAt": retrieved_at,
            "responseSha256": "",
            "contentType": "",
            "reachable": False,
            "currentYearActiveSignal": "",
            "activeEvidenceExcerpt": "",
            "explicitClosureSignal": "",
            "error": str(exc)[:500],
        }


def main() -> int:
    args = parse_args()
    state = args.state.upper()
    entities_path = ROOT / "research" / "state-expansions" / state / "entities.csv"
    with entities_path.open(newline="", encoding="utf-8") as handle:
        entities = list(csv.DictReader(handle))
    by_url: dict[str, list[str]] = {}
    for row in entities:
        url = row.get("website_url", "").strip()
        if url:
            by_url.setdefault(url, []).append(row["entity_id"])
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(fetch, url): url for url in sorted(by_url)}
        for future in as_completed(futures):
            url = futures[future]
            result = future.result()
            result["entityIds"] = by_url[url]
            results.append(result)
    results.sort(key=lambda row: row["requestedUrl"])
    output = ROOT / "data" / "source-releases" / "work" / state / "operation-web-audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "state": state,
        "websites": len(results),
        "reachable": sum(row["reachable"] for row in results),
        "currentYearActiveSignal": sum(bool(row["currentYearActiveSignal"]) for row in results),
        "explicitClosureSignal": sum(bool(row["explicitClosureSignal"]) for row in results),
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
