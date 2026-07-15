#!/usr/bin/env python3
"""Apply the shared URL classification to one committed state entity table."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from state_release_urls import classify_public_urls


ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state")
    args = parser.parse_args()
    state = args.state.upper()
    path = ROOT / "research" / "state-expansions" / state / "entities.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    changed = 0
    for row in rows:
        before = tuple(row.get(field, "") for field in
                       ("website_url", "facebook_url", "instagram_url", "tiktok_url"))
        after = classify_public_urls(*before)
        if before != after:
            changed += 1
            for field, value in zip(("website_url", "facebook_url", "instagram_url", "tiktok_url"), after):
                row[field] = value
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{state}: normalized public URLs for {changed} entities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
