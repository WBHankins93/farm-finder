#!/usr/bin/env python3
"""Compatibility wrapper for the shared state-release validator."""

from __future__ import annotations

import json

from validate_state_releases import validate_state


def main() -> int:
    result = validate_state("AL", require_local_artifacts=False)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
